#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import ctypes
import winreg
import subprocess
import shutil
import time
import platform
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path

# İşlem detaylarını gösterip göstermeme
QUIET_MODE = True

def is_admin():
    """Kullanıcının admin haklarına sahip olup olmadığını kontrol eder"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def check_python_version():
    """Python sürümünü kontrol eder"""
    required_version = (3, 6)
    current_version = sys.version_info
    
    if current_version.major < required_version[0] or (current_version.major == required_version[0] and current_version.minor < required_version[1]):
        print(f"[-] Python {required_version[0]}.{required_version[1]} veya üzeri gereklidir.")
        print(f"    Mevcut sürüm: Python {current_version.major}.{current_version.minor}")
        print(f"    Lütfen Python'u güncelleyin: https://www.python.org/downloads/")
        return False
    return True

def create_license_key():
    """Lisans anahtarı oluşturur"""
    if not QUIET_MODE:
        print("[+] Lisans anahtarı oluşturuluyor...")
    
    # Kullanıcının istediği lisans içeriği
    license_content = """RAR registration data
Hououin Kyouma
El Psy Congroo
UID=c881245b7b1a78985cb0
64122122505cb05c44e75618ab5ea84c86e876e620d42d566d4453
18f59893063b0c337398603ef609acfb0eac3505bc19e61df2b7f5
bba0aeef9172868794c0d6b2314c038d105f9b3ba638ec8a82305b
a209c087680d071cbbdbb10a9652f8c2b06091a5243fbbc24b381d
4cb3b58c52c3d7d99b828c76f88937dd4d94058fb3038d105f9b3b
a638ec8aa57606488b324a1e71be06e54787b797df438679604ee6
92b1f552734e6580bee03078379b0cdddee16bb6f4a53644961125
"""
    
    success_count = 0
    failed_locations = []
    
    # Birden fazla olası konum - Bazı durumlar için farklı yerler gerekebilir
    locations = [
        # 1. APPDATA klasörü - birçok kullanıcı için çalışır
        os.path.join(os.environ.get('APPDATA', ''), 'WinRAR', 'rarreg.key'),
        
        # 2. Program Files - Admin hakları gerekli
        os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'WinRAR', 'rarreg.key'),
        os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'WinRAR', 'rarreg.key'),
        
        # 3. ALLUSERSPROFILE - sistem çapında ayarlar
        os.path.join(os.environ.get('ALLUSERSPROFILE', 'C:\\ProgramData'), 'WinRAR', 'rarreg.key'),
        
        # 4. Windows klasörü - bazı eski sürümler için
        os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'System32', 'rarreg.key')
    ]
    
    # WinRAR programını bul
    winrar_path = find_winrar_path()
    if winrar_path:
        # Program Files içindeki kurulum klasörüne ekle
        locations.append(os.path.join(winrar_path, 'rarreg.key'))
    
    for path in locations:
        try:
            # Klasörü oluştur
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            # Lisans dosyasını yaz
            with open(path, 'w') as f:
                f.write(license_content)
            
            # Dosya izinlerini ayarla - herkes için okunabilir
            try:
                os.chmod(path, 0o444)  # Salt okunur (Read-only)
            except:
                pass
                
            success_count += 1
            if not QUIET_MODE:
                print(f"[✓] Lisans dosyası oluşturuldu: {path}")
        except Exception as e:
            failed_locations.append(path)
            if not QUIET_MODE:
                print(f"[-] Lisans dosyası oluşturulamadı: {path}")
    
    if success_count > 0:
        return True
    else:
        if not QUIET_MODE:
            print("[-] Hiçbir konumda lisans dosyası oluşturulamadı!")
        return False

def modify_registry():
    """Registry anahtarlarını değiştirir - hem HKCU hem de HKLM"""
    if not QUIET_MODE:
        print("[+] Registry ayarları değiştiriliyor...")
    
    success_count = 0
    
    # 1. HKEY_CURRENT_USER değişiklikleri
    try:
        # Registry anahtarı
        reg_path = r"SOFTWARE\WinRAR\Licenses"
        
        # Registry anahtarı oluştur veya aç
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE)
        except:
            key = winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE)
        
        # Lisans bilgilerini ayarla - 50 yıl
        future_date = datetime.now() + timedelta(days=365*50)
        license_date = future_date.strftime("%Y%m%d")
        
        winreg.SetValueEx(key, "LicenseKey", 0, winreg.REG_SZ, "c881245b7b1a78985cb0")
        winreg.SetValueEx(key, "LicenseName", 0, winreg.REG_SZ, "Hououin Kyouma")
        winreg.SetValueEx(key, "LicenseExpiry", 0, winreg.REG_SZ, license_date)
        winreg.SetValueEx(key, "LicenseType", 0, winreg.REG_SZ, "Unlimited")
        
        winreg.CloseKey(key)
        if not QUIET_MODE:
            print("[✓] HKEY_CURRENT_USER registry güncellendi")
        success_count += 1
    except Exception as e:
        if not QUIET_MODE:
            print(f"[-] HKEY_CURRENT_USER registry değiştirilemedi")
    
    # 2. HKEY_LOCAL_MACHINE değişiklikleri (admin hakları gerekli)
    try:
        # Ana Registry anahtarı
        reg_path = r"SOFTWARE\WinRAR\Licenses"
        
        # 32-bit ve 64-bit sistemler için Registry anahtarı oluştur
        for access_type in [winreg.KEY_WOW64_32KEY | winreg.KEY_WRITE, winreg.KEY_WOW64_64KEY | winreg.KEY_WRITE]:
            try:
                try:
                    key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, access_type)
                except:
                    key = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, access_type)
                
                # Lisans bilgilerini ayarla
                future_date = datetime.now() + timedelta(days=365*50)
                license_date = future_date.strftime("%Y%m%d")
                
                winreg.SetValueEx(key, "LicenseKey", 0, winreg.REG_SZ, "c881245b7b1a78985cb0")
                winreg.SetValueEx(key, "LicenseName", 0, winreg.REG_SZ, "Hououin Kyouma")
                winreg.SetValueEx(key, "LicenseExpiry", 0, winreg.REG_SZ, license_date)
                winreg.SetValueEx(key, "LicenseType", 0, winreg.REG_SZ, "Unlimited")
                
                winreg.CloseKey(key)
                if not QUIET_MODE:
                    print("[✓] HKEY_LOCAL_MACHINE registry güncellendi")
                success_count += 1
            except Exception:
                if not QUIET_MODE:
                    print(f"[-] HKEY_LOCAL_MACHINE registry değiştirilemedi")
                
    except Exception:
        pass
    
    # 3. WinRAR ana ayarları değiştir - deneme süresi gösterimini kapat
    try:
        reg_path = r"SOFTWARE\WinRAR\General"
        
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE)
        except:
            key = winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE)
            
        # Farklı değerler ayarla
        winreg.SetValueEx(key, "ShowLicense", 0, winreg.REG_DWORD, 0)  # Lisans gösterimini kapat
        winreg.SetValueEx(key, "InstallVersion", 0, winreg.REG_SZ, "6.00")  # Sürümü ayarla
        
        winreg.CloseKey(key)
        if not QUIET_MODE:
            print("[✓] WinRAR genel ayarları güncellendi")
        success_count += 1
    except Exception:
        if not QUIET_MODE:
            print(f"[-] WinRAR genel ayarları değiştirilemedi")
    
    if success_count > 0:
        return True
    else:
        return False

def find_winrar_path():
    """WinRAR'ın kurulu olduğu dizini bulur"""
    possible_paths = [
        r"C:\Program Files\WinRAR",
        r"C:\Program Files (x86)\WinRAR",
    ]
    
    # Özel kurulumları kontrol et
    for drive in "CDEFGH":
        possible_paths.append(f"{drive}:\\WinRAR")
        possible_paths.append(f"{drive}:\\Program Files\\WinRAR")
        possible_paths.append(f"{drive}:\\Program Files (x86)\\WinRAR")
    
    for path in possible_paths:
        if os.path.exists(path) and os.path.isfile(os.path.join(path, "WinRAR.exe")):
            return path
    
    return None

def check_winrar_installed():
    """WinRAR'ın kurulu olup olmadığını kontrol eder"""
    winrar_path = find_winrar_path()
    if not winrar_path:
        print("[-] WinRAR kurulumu bulunamadı.")
        print("    WinRAR'ı https://www.rarlab.com/download.htm adresinden indirebilirsiniz.")
        return False
    
    print(f"[✓] WinRAR kurulumu bulundu: {winrar_path}")
    return True

def reset_winrar_trial():
    """WinRAR deneme süresini sıfırlar"""
    if not QUIET_MODE:
        print("[+] WinRAR deneme süresi sıfırlanıyor...")
    
    try:
        # 1. HKEY_CURRENT_USER içerisindeki WinRAR bilgilerini temizle
        cu_reg_paths = [
            r"SOFTWARE\WinRAR",
            r"SOFTWARE\WinRAR\Licenses",
            r"SOFTWARE\WinRAR\General",
            r"SOFTWARE\WinRAR\DialogEditHistory\ExtrPath"
        ]
        
        for path in cu_reg_paths:
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
            except:
                pass
        
        # 2. HKEY_LOCAL_MACHINE içerisindeki WinRAR bilgilerini temizle
        lm_reg_paths = [
            r"SOFTWARE\WinRAR",
            r"SOFTWARE\WinRAR\Licenses",
            r"SOFTWARE\WinRAR\General"
        ]
        
        for path in lm_reg_paths:
            for access_type in [winreg.KEY_WOW64_32KEY | winreg.KEY_WRITE, winreg.KEY_WOW64_64KEY | winreg.KEY_WRITE]:
                try:
                    winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, path)
                except:
                    pass
        
        # 3. %APPDATA% ve diğer klasörlerdeki WinRAR dizinlerini temizle
        directories_to_clean = [
            os.path.join(os.environ.get('APPDATA', ''), 'WinRAR'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'WinRAR'),
            os.path.join(os.environ.get('ALLUSERSPROFILE', 'C:\\ProgramData'), 'WinRAR')
        ]
        
        for directory in directories_to_clean:
            if os.path.exists(directory):
                try:
                    shutil.rmtree(directory, ignore_errors=True)
                except:
                    pass
        
        if not QUIET_MODE:
            print("[✓] WinRAR deneme süresi sıfırlandı")
        return True
    except Exception:
        if not QUIET_MODE:
            print(f"[-] Deneme süresi sıfırlanamadı")
        return False

def delete_existing_rarreg():
    """Mevcut rarreg.key dosyalarını bulup siler"""
    if not QUIET_MODE:
        print("[+] Mevcut rarreg.key dosyaları aranıyor...")
    
    found_files = []
    
    # Olası konumlar
    drives = ['C:', 'D:', 'E:', 'F:']
    possible_locations = [
        r"\Program Files\WinRAR",
        r"\Program Files (x86)\WinRAR",
        r"\WinRAR",
        r"\Windows",
        r"\Windows\System32"
    ]
    
    # Kullanıcı profilleri
    for drive in drives:
        for location in possible_locations:
            path = f"{drive}{location}\\rarreg.key"
            if os.path.exists(path):
                found_files.append(path)
    
    # Kullanıcı profilleri içinde de ara
    users_dir = os.path.join(os.environ.get('SystemDrive', 'C:'), 'Users')
    if os.path.exists(users_dir):
        for user_dir in os.listdir(users_dir):
            appdata_path = os.path.join(users_dir, user_dir, 'AppData')
            if os.path.exists(appdata_path):
                # Roaming AppData
                rarreg_path = os.path.join(appdata_path, 'Roaming', 'WinRAR', 'rarreg.key')
                if os.path.exists(rarreg_path):
                    found_files.append(rarreg_path)
                
                # Local AppData
                rarreg_path = os.path.join(appdata_path, 'Local', 'WinRAR', 'rarreg.key')
                if os.path.exists(rarreg_path):
                    found_files.append(rarreg_path)
    
    # Dosyaları sil
    deleted_count = 0
    for file_path in found_files:
        try:
            os.chmod(file_path, 0o777)  # Önce izinleri değiştir
            os.remove(file_path)
            if not QUIET_MODE:
                print(f"[✓] Eski lisans dosyası silindi: {file_path}")
            deleted_count += 1
        except Exception:
            if not QUIET_MODE:
                print(f"[-] Dosya silinemedi: {file_path}")
    
    if found_files and not QUIET_MODE:
        print(f"[✓] Toplam {deleted_count}/{len(found_files)} eski lisans dosyası temizlendi")
    elif not found_files and not QUIET_MODE:
        print("[i] Eski lisans dosyası bulunamadı")
    
    return deleted_count > 0

def force_kill_processes():
    """WinRAR ile ilgili tüm süreçleri sonlandırır"""
    if not QUIET_MODE:
        print("[+] WinRAR süreçleri sonlandırılıyor...")
    
    processes_to_kill = ["WinRAR.exe", "Rar.exe", "UnRAR.exe"]
    
    for process in processes_to_kill:
        try:
            subprocess.run(["taskkill", "/f", "/im", process], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
        except:
            pass
    
    # Biraz bekle
    time.sleep(1)
    
    return True

def print_ascii_logo():
    """ASCII logoyu ekrana yazdırır"""
    logo = """
 ██╗    ██╗██╗███╗   ██╗██████╗  █████╗ ██████╗ 
 ██║    ██║██║████╗  ██║██╔══██╗██╔══██╗██╔══██╗
 ██║ █╗ ██║██║██╔██╗ ██║██████╔╝███████║██████╔╝
 ██║███╗██║██║██║╚██╗██║██╔══██╗██╔══██║██╔══██╗
 ╚███╔███╔╝██║██║ ╚████║██║  ██║██║  ██║██║  ██║
  ╚══╝╚══╝ ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
================================================
        WinRAR Aktivatoru - by Kynarix
================================================
"""
    print(logo)

def check_os():
    """İşletim sistemi uyumluluğunu kontrol eder"""
    if not platform.system() == "Windows":
        print(f"[-] Bu program sadece Windows işletim sistemlerinde çalışır.")
        print(f"    Mevcut işletim sistemi: {platform.system()}")
        return False
    
    return True

def is_discord_running():
    """Discord'un çalışıp çalışmadığını kontrol eder"""
    try:
        # Discord process'lerini kontrol et
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Discord.exe", "/NH"], 
            capture_output=True, 
            text=True, 
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        # Eğer çıktıda "Discord.exe" varsa, Discord çalışıyordur
        return "Discord.exe" in result.stdout
    except Exception:
        # Herhangi bir hata olursa, Discord'un çalışmadığını varsay
        return False

def open_discord_server():
    """Discord sunucusunu açar (discord.gg/codejs)"""
    print("\n[+] Discord sunucumuza katılmak ister misiniz? (E/H): ", end="")
    choice = input().strip().lower()
    
    if choice == 'e' or choice == 'evet':
        discord_invite_url = "https://discord.gg/codejs"
        discord_app_url = "discord://discord.gg/codejs"
        
        try:
            # Discord çalışıyor mu kontrol et
            if is_discord_running():
                print("[+] Discord uygulaması üzerinden sunucuya yönlendiriliyorsunuz...")
                # Discord protokolünü kullanarak sunucuya yönlendir
                webbrowser.open(discord_app_url)
            else:
                print("[+] Tarayıcı üzerinden Discord sunucusuna yönlendiriliyorsunuz...")
                # Tarayıcı üzerinden Discord sunucusuna yönlendir
                webbrowser.open(discord_invite_url)
            
            print(f"[i] Discord sunucusu: {discord_invite_url}")
            return True
        except Exception:
            print(f"[-] Discord sunucusuna yönlendirme başarısız oldu.")
            print(f"[i] Manuel olarak katılmak için: {discord_invite_url}")
            return False
    else:
        print("[i] Discord sunucumuza katılmayı tercih etmediniz.")
        return False

def main():
    # Renkli konsol çıktısı için Windows'ta ANSI çıktıları etkinleştir
    os.system("")
    
    # Konsolu temizle
    os.system('cls' if os.name == 'nt' else 'clear')
    
    # Logoyu göster
    print_ascii_logo()
    
    print("WinRAR aktivatoru baslatiliyor...")
    print()
    
    # İşletim sistemi kontrolü
    if not check_os():
        input("\nÇıkmak için bir tuşa basın...")
        sys.exit(1)
    
    # Python sürüm kontrolü
    if not check_python_version():
        input("\nÇıkmak için bir tuşa basın...")
        sys.exit(1)
    
    # Admin kontrolü
    if not is_admin():
        print("[-] Bu aktivatörün düzgün çalışması için admin hakları gerekli!")
        print("    Lütfen bu scripti admin olarak çalıştırın...")
        
        # Tekrar admin olarak çalıştırmayı dene
        if sys.platform == 'win32':
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        
        input("\nÇıkmak için bir tuşa basın...")
        sys.exit(1)
    
    # WinRAR kurulu mu kontrol et
    if not check_winrar_installed():
        input("\nÇıkmak için bir tuşa basın...")
        sys.exit(1)
    
    # Aktivasyon işlemleri
    print("\n[+] AKTIVATOR BASLATILIYOR!")
    print("="*50)
    print("\n[!] LUTFEN BEKLEYIN! Bu islem biraz zaman alabilir...")
    
    # İşlemleri yap ama çıktıları gösterme
    force_kill_processes()
    delete_existing_rarreg()
    reset_winrar_trial()
    license_success = create_license_key()
    registry_success = modify_registry()
    
    # Sonucu göster
    print("\n" + "="*50)
    
    if license_success and registry_success:
        print("\n[+] İşlem başarılı oldu! WinRAR artık FULL VERSİYON!")
    else:
        print("\n[-] Aktivasyon kısmen başarılı veya başarısız oldu.")
        print("[-] Bu sisteme özel bir ayar gerekebilir.")
    
    print("\n[!] WinRAR'ı açarak aktivasyonu test edin.")
    print("[+] Problem yasarsaniz, aktivatoru tekrar calistirin.")
    print("="*50)
    print("by Kynarix tarafından yapılmıştır")
    print("\n[Github]: https://github.com/Kynarix")
    
    # Discord sunucusuna yönlendirme
    open_discord_server()
    
    input("\nÇıkmak için bir tuşa basın...")

if __name__ == "__main__":
    main() 