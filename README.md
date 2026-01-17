# RenForge - 2 Tikla Push (All-in-One v2)

Bu surum, "untracked dosyalar var / nothing added to commit" hatasini cozer.

## Kurulum
1) Zip icindeki iki dosyayi repo kokune kopyala:
   `D:\Kodlama\RnpyCeviri\RenForge -2`
   - RenForge_Push.cmd
   - rfpush_gui.ps1

2) `RenForge_Push.cmd` sag tik -> Gonder -> Masaustu (kısayol olustur)

## Kullanim
- Masaustundeki kısayola cift tik
- Mesaji yaz (bos = WIP)
- Eger sadece yeni dosyalar varsa, "hepsini ekleyeyim mi?" diye sorar

## Tavsiye
Sende zip ve .bak dosyalari cok gorunuyor. Bunlari commit'e sokmek istemiyorsan `.gitignore`'a su satirlari ekle:
- *.zip
- *.bak
- .agent/
- .venv/
- __pycache__/
