import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
import subprocess
import sys
import os

# KRİTİK EKLEME: PyInstaller ile paketlendiğinde logonun bulunabilmesi için
def kaynak_yolu(goreceli_yol):
    """ Dosyaların (logo vs.) mutlak yolunu bulur, PyInstaller ile tam uyumludur. """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, goreceli_yol)

try:
    from PIL import Image, ImageTk
    PILLOW_MEVCUT = True
except ImportError:
    PILLOW_MEVCUT = False
    print("Uyarı: Pillow kütüphanesi bulunamadı. Logo standart yöntemle yüklenecek.")

# --- 1. SEKME SINIFI ---
class EditorSekmesi(ttk.Frame):
    def __init__(self, notebook, parent_app, dosya_yolu=None):
        super().__init__(notebook)
        self.notebook = notebook
        self.parent_app = parent_app 
        self.dosya_yolu = dosya_yolu
        self._renklendir_id = None
        self.yazi_boyutu = 14
        self.degisti = False

        self.satir_numaralari = tk.Canvas(self, width=45, bg="#1E1E1E", highlightthickness=0)
        self.satir_numaralari.pack(side="left", fill="y")

        self.text_alani = tk.Text(self, wrap="none", undo=True, font=("Ubuntu Mono", self.yazi_boyutu), 
                                 bg="#1E1E1E", fg="#ABB2BF", insertbackground="white")
        self.text_alani.pack(expand=True, fill="both")

        self.y_scroll = tk.Scrollbar(self.text_alani, command=self.sync_scroll)
        self.y_scroll.pack(side="right", fill="y")
        self.text_alani.config(yscrollcommand=self.on_vscroll)

        self.text_alani.bind("<KeyRelease>", self.on_key_release)
        self.text_alani.bind("<Button-4>", self.on_mouse_wheel)
        self.text_alani.bind("<Button-5>", self.on_mouse_wheel)
        self.text_alani.bind("<Button-1>", lambda e: self.after(1, self.ui_guncelle))
        
        self.text_alani.bind("<Control-z>", self.undo_action)
        self.text_alani.bind("<Control-y>", self.redo_action)
        self.text_alani.bind("<Control-a>", self.hepsini_sec)
        self.text_alani.bind("<Control-d>", self.satir_cogalt) 
        self.text_alani.bind("<Return>", self.auto_indent)

        self.text_alani.tag_config("keyword", foreground="#C678DD")   
        self.text_alani.tag_config("func_name", foreground="#E5C07B") 
        self.text_alani.tag_config("string", foreground="#98C379")    
        self.text_alani.tag_config("number", foreground="#D19A66")    
        self.text_alani.tag_config("comment", foreground="#5C6370")   
        self.text_alani.tag_config("active_line", background="#2C313C")
        self.text_alani.tag_config("match", background="#61AFEF", foreground="black")

        self.text_alani.tag_raise("active_line")

    def ui_guncelle(self):
        self.update_line_numbers()
        self.highlight_current_line()
        self.parent_app.update_status_bar()

    def zoom(self, delta):
        self.yazi_boyutu = max(8, self.yazi_boyutu + delta)
        self.text_alani.config(font=("Ubuntu Mono", self.yazi_boyutu))
        self.ui_guncelle()

    def highlight_current_line(self):
        self.text_alani.tag_remove("active_line", "1.0", tk.END)
        self.text_alani.tag_add("active_line", "insert linestart", "insert lineend + 1c")

    def satir_cogalt(self, event=None):
        line_content = self.text_alani.get("insert linestart", "insert lineend")
        self.text_alani.insert("insert lineend", "\n" + line_content)
        self.on_key_release()
        return "break"

    def auto_indent(self, event):
        satir = self.text_alani.get("insert linestart", "insert")
        eslesme = re.match(r'^(\s+)', satir)
        bosluklar = eslesme.group(1) if eslesme else ""
        if satir.strip().endswith(":"):
            bosluklar += "    "
        self.text_alani.insert(tk.INSERT, f"\n{bosluklar}")
        self.text_alani.see(tk.INSERT)
        self.after(1, self.ui_guncelle)
        return "break"

    def hepsini_sec(self, event=None):
        self.text_alani.tag_add(tk.SEL, "1.0", tk.END)
        return "break"

    def on_mouse_wheel(self, event):
        if event.state & 0x0004: 
            if event.num == 4: self.zoom(1)
            elif event.num == 5: self.zoom(-1)
            return "break" 
        self.after(1, self.ui_guncelle)

    def on_vscroll(self, *args):
        self.y_scroll.set(*args)
        self.update_line_numbers()

    def sync_scroll(self, *args):
        self.text_alani.yview(*args)
        self.update_line_numbers()

    def update_line_numbers(self, event=None):
        self.satir_numaralari.delete("all")
        i = self.text_alani.index("@0,0")
        while True:
            dline = self.text_alani.dlineinfo(i)
            if dline is None: break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.satir_numaralari.create_text(38, y, anchor="ne", text=linenum, fill="#4B5263", font=("Ubuntu Mono", 11))
            i = self.text_alani.index("%s+1line" % i)

    def undo_action(self, event=None):
        try: self.text_alani.edit_undo()
        except tk.TclError: pass
        self.after(1, self.ui_guncelle)
        self.renklendir()
        return "break"

    def redo_action(self, event=None):
        try: self.text_alani.edit_redo()
        except tk.TclError: pass
        self.after(1, self.ui_guncelle)
        self.renklendir()
        return "break"

    def on_key_release(self, event=None):
        if event and event.keysym not in ["Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R"]:
            if not self.degisti:
                self.degisti = True
                self.parent_app.update_tab_name(self)

        self.after(1, self.ui_guncelle)
        if self._renklendir_id:
            self.after_cancel(self._renklendir_id)
        self._renklendir_id = self.after(200, self.renklendir)

    def renklendir(self):
        icerik = self.text_alani.get("1.0", tk.END)
        for etiket in ["keyword", "func_name", "string", "number", "comment"]:
            self.text_alani.tag_remove(etiket, "1.0", tk.END)

        kurallar = [
            ("number", r'\b\d+\b'),
            ("keyword", r'\b(def|class|import|from|return|if|elif|else|for|while|try|except|with|as|pass|and|or|not|in|is|lambda|global|True|False|None|int|char|float|double|void|#include)\b'),
            ("func_name", r'\b(?:def|class)\s+([a-zA-Z_]\w*)'),
            ("string", r'\"\"\"[\s\S]*?\"\"\"|\'\'\'[\s\S]*?\'\'\'|\"[^\"\n]*\"|\'[^\'\n]*\''),
            ("comment", r'#.*|//.*|/\*[\s\S]*?\*/')
        ]

        for etiket, regex in kurallar:
            for match in re.finditer(regex, icerik, re.MULTILINE):
                start = f"1.0+{match.start(1)}c" if match.lastindex else f"1.0+{match.start()}c"
                end = f"1.0+{match.end(1)}c" if match.lastindex else f"1.0+{match.end()}c"
                self.text_alani.tag_add(etiket, start, end)

# --- 2. ANA UYGULAMA SINIFI ---
class Editor:
    def __init__(self, pencere):
        self.pencere = pencere
        self.pencere.title("Artvin Editör")
        self.pencere.geometry("1100x750")

        # Yedekli Logo Yükleme Mekanizması
        try:
            logo_yolu = kaynak_yolu("logo.png")
            if os.path.exists(logo_yolu):
                if PILLOW_MEVCUT:
                    pil_img = Image.open(logo_yolu).convert("RGBA")
                    self.logo_img = ImageTk.PhotoImage(pil_img)
                else:
                    self.logo_img = tk.PhotoImage(file=logo_yolu)
                
                self.pencere.iconphoto(True, self.logo_img)
        except Exception as e:
            print(f"Logo yüklenirken bir hata oluştu: {e}")

        # Stil Ayarları
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background='#21252B', borderwidth=0)
        style.configure('TNotebook.Tab', background='#282C34', foreground='#ABB2BF', padding=[15, 5])
        style.map('TNotebook.Tab', background=[('selected', '#1E1E1E')], foreground=[('selected', '#FFFFFF')])

        self.notebook = ttk.Notebook(self.pencere)
        self.notebook.pack(expand=True, fill="both")

        # Status Bar
        self.status_bar = tk.Label(self.pencere, text="Ln 1, Col 0", bd=1, relief=tk.SUNKEN, anchor=tk.E, bg="#21252B", fg="#ABB2BF")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.menu_olustur()
        self.yeni_sekme() 

        # Global Kısayollar
        self.pencere.bind("<Control-n>", lambda e: self.yeni_sekme())
        self.pencere.bind("<Control-t>", lambda e: self.yeni_sekme())
        self.pencere.bind("<Control-o>", lambda e: self.dosya_ac()) 
        self.pencere.bind("<Control-s>", lambda e: self.dosya_kaydet())
        self.pencere.bind("<Control-w>", lambda e: self.sekmeyi_kapat())
        self.pencere.bind("<Control-f>", lambda e: self.bul_penceresi())
        
        # Klavye Zoom Kısayolları
        self.pencere.bind("<Control-plus>", lambda e: self.guncel_sekme().zoom(1) if self.guncel_sekme() else None)
        self.pencere.bind("<Control-KP_Add>", lambda e: self.guncel_sekme().zoom(1) if self.guncel_sekme() else None)
        self.pencere.bind("<Control-minus>", lambda e: self.guncel_sekme().zoom(-1) if self.guncel_sekme() else None)
        self.pencere.bind("<Control-KP_Subtract>", lambda e: self.guncel_sekme().zoom(-1) if self.guncel_sekme() else None)

    def update_status_bar(self):
        sekme = self.guncel_sekme()
        if sekme:
            pos = sekme.text_alani.index(tk.INSERT)
            ln, col = pos.split('.')
            self.status_bar.config(text=f"Ln {ln}, Col {col}")

    def update_tab_name(self, sekme):
        try:
            idx = self.notebook.index(sekme)
            text = self.notebook.tab(idx, "text")
            if sekme.degisti and not text.endswith("*"):
                self.notebook.tab(idx, text=text + " *")
            elif not sekme.degisti and text.endswith("*"):
                self.notebook.tab(idx, text=text[:-2])
        except: pass

    def guncel_sekme(self):
        secili_id = self.notebook.select()
        return self.pencere.nametowidget(secili_id) if secili_id else None

    def yeni_sekme(self, dosya_yolu=None, icerik=""):
        sekme = EditorSekmesi(self.notebook, self, dosya_yolu=dosya_yolu)
        if icerik:
            sekme.text_alani.insert(tk.END, icerik)
            sekme.update_line_numbers()
            sekme.renklendir()
            
        baslik = os.path.basename(dosya_yolu) if dosya_yolu else "İsimsiz"
        self.notebook.add(sekme, text=baslik)
        self.notebook.select(sekme) 
        sekme.ui_guncelle()
        return sekme

    def sekmeyi_kapat(self, event=None):
        sekme = self.guncel_sekme()
        if sekme:
            if sekme.degisti:
                cvp = messagebox.askyesnocancel("Kaydedilmemiş Değişiklik", "Değişiklikleri kaydetmek ister misiniz?")
                if cvp: self.dosya_kaydet(); self.notebook.forget(sekme); sekme.destroy()
                elif cvp is False: self.notebook.forget(sekme); sekme.destroy()
            else:
                self.notebook.forget(sekme); sekme.destroy()

    def bul_penceresi(self):
        bul_win = tk.Toplevel(self.pencere)
        bul_win.title("Bul")
        bul_win.geometry("350x120")
        bul_win.transient(self.pencere)
        tk.Label(bul_win, text="Aranacak Kelime:").pack(pady=5)
        entry = tk.Entry(bul_win)
        entry.pack(fill=tk.X, padx=20)
        entry.focus_set()
        
        def ara():
            sekme = self.guncel_sekme()
            if not sekme: return
            sekme.text_alani.tag_remove("match", "1.0", tk.END)
            s = entry.get()
            if s:
                idx = "1.0"
                while True:
                    idx = sekme.text_alani.search(s, idx, nocase=1, stopindex=tk.END)
                    if not idx: break
                    lastidx = f"{idx}+{len(s)}c"
                    sekme.text_alani.tag_add("match", idx, lastidx)
                    idx = lastidx
        
        tk.Button(bul_win, text="Hepsini Vurgula", command=ara).pack(pady=10)

    def menu_olustur(self):
        menu_cubugu = tk.Menu(self.pencere)
        self.pencere.config(menu=menu_cubugu)

        dosya = tk.Menu(menu_cubugu, tearoff=0)
        menu_cubugu.add_cascade(label="Dosya", menu=dosya)
        dosya.add_command(label="Yeni Sekme (Ctrl+N)", command=self.yeni_sekme)
        dosya.add_command(label="Aç (Ctrl+O)", command=self.dosya_ac)
        dosya.add_separator()
        dosya.add_command(label="Kaydet (Ctrl+S)", command=self.dosya_kaydet)
        dosya.add_command(label="Farklı Kaydet", command=lambda: self.dosya_kaydet(farkli=True))
        dosya.add_separator()
        dosya.add_command(label="Sekmeyi Kapat (Ctrl+W)", command=self.sekmeyi_kapat)
        dosya.add_command(label="Çıkış", command=self.pencere.quit)

        duzen = tk.Menu(menu_cubugu, tearoff=0)
        menu_cubugu.add_cascade(label="Düzenle", menu=duzen)
        duzen.add_command(label="Geri Al (Ctrl+Z)", command=lambda: self.guncel_sekme().undo_action() if self.guncel_sekme() else None)
        duzen.add_command(label="Yinele (Ctrl+Y)", command=lambda: self.guncel_sekme().redo_action() if self.guncel_sekme() else None)
        duzen.add_separator()
        duzen.add_command(label="Bul (Ctrl+F)", command=self.bul_penceresi)
        duzen.add_separator()
        duzen.add_command(label="Kes (Ctrl+X)", command=lambda: self.pencere.focus_get().event_generate("<<Cut>>"))
        duzen.add_command(label="Kopyala (Ctrl+C)", command=lambda: self.pencere.focus_get().event_generate("<<Copy>>"))
        duzen.add_command(label="Yapıştır (Ctrl+V)", command=lambda: self.pencere.focus_get().event_generate("<<Paste>>"))
        duzen.add_separator()
        duzen.add_command(label="Tümünü Seç (Ctrl+A)", command=lambda: self.guncel_sekme().hepsini_sec() if self.guncel_sekme() else None)
        duzen.add_command(label="Satırı Çoğalt (Ctrl+D)", command=lambda: self.guncel_sekme().satir_cogalt() if self.guncel_sekme() else None)

        araclar = tk.Menu(menu_cubugu, tearoff=0)
        menu_cubugu.add_cascade(label="Araçlar", menu=araclar)
        araclar.add_command(label="Kodu Çalıştır (F5)", command=self.kodu_calistir)

    def dosya_ac(self):
        path = filedialog.askopenfilename()
        if path:
            with open(path, "r", encoding="utf-8") as f:
                icerik = f.read()
            self.yeni_sekme(dosya_yolu=path, icerik=icerik)
            self.pencere.title(f"Artvin Editör - {path}")

    def dosya_kaydet(self, farkli=False):
        sekme = self.guncel_sekme()
        if not sekme: return

        if farkli or not sekme.dosya_yolu or not os.path.exists(sekme.dosya_yolu):
            yeni_yol = filedialog.asksaveasfilename(defaultextension=".py")
            if not yeni_yol: return 
            sekme.dosya_yolu = yeni_yol

        with open(sekme.dosya_yolu, "w", encoding="utf-8") as f:
            f.write(sekme.text_alani.get(1.0, tk.END))
        
        sekme.degisti = False
        self.update_tab_name(sekme)
        self.notebook.tab(sekme, text=os.path.basename(sekme.dosya_yolu))
        self.pencere.title(f"Artvin Editör - {sekme.dosya_yolu}")

    def kodu_calistir(self):
        sekme = self.guncel_sekme()
        if not sekme or not sekme.dosya_yolu: return
        self.dosya_kaydet()
        yol = sekme.dosya_yolu
        if yol.endswith(".py"):
            komut = f"bash -c 'python3 \"{yol}\"; echo; read -p \"Bitti...\"'"
        elif yol.endswith((".c", ".cpp")):
            output = yol.replace(".cpp", "").replace(".c", "")
            komut = f"bash -c 'g++ \"{yol}\" -o \"{output}\" && \"./{output}\"; echo; read -p \"Bitti...\"'"
        else: return
        subprocess.Popen(['x-terminal-emulator', '-e', komut], stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    # KRİTİK DEĞİŞİKLİK: Alt+Tab desteği (WM_CLASS) burada ana pencere yaratılırken verilir.
    root = tk.Tk(className="artvineditor")
    app = Editor(root)
    root.mainloop()
