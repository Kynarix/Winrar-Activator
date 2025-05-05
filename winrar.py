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

QUIET_MODE = True

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def check_python_version():
    required_version = (3, 6)
    current_version = sys.version_info
    
    if current_version.major < required_version[0] or (current_version.major == required_version[0] and current_version.minor < required_version[1]):
        print(f"[-] Python {required_version[0]}.{required_version[1]} veya üzeri gereklidir.")
        print(f"    Mevcut sürüm: Python {current_version.major}.{current_version.minor}")
        print(f"    Lütfen Python'u güncelleyin: https://www.python.org/downloads/")
        return False
    return True

def create_license_key():
    if not QUIET_MODE:
        print("[+] Lisans anahtarı oluşturuluyor...")
    
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
    
    locations = [
        os.path.join(os.environ.get('APPDATA', ''), 'WinRAR', 'rarreg.key'),
        os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), 'WinRAR', 'rarreg.key'),
        os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'), 'WinRAR', 'rarreg.key'),
        os.path.join(os.environ.get('ALLUSERSPROFILE', 'C:\\ProgramData'), 'WinRAR', 'rarreg.key'),
        os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'System32', 'rarreg.key')
    ]
    
    winrar_path = find_winrar_path()
    if winrar_path:
        locations.append(os.path.join(winrar_path, 'rarreg.key'))
    
    for path in locations:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            with open(path, 'w') as f:
                f.write(license_content)
            
            try:
                os.chmod(path, 0o444)
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
    if not QUIET_MODE:
        print("[+] Registry ayarları değiştiriliyor...")
    
    success_count = 0
    
    try:
        reg_path = r"SOFTWARE\WinRAR\Licenses"
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE)
        except:
            key = winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE)
        
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
    
    try:
        reg_path = r"SOFTWARE\WinRAR\Licenses"
        for access_type in [winreg.KEY_WOW64_32KEY | winreg.KEY_WRITE, winreg.KEY_WOW64_64KEY | winreg.KEY_WRITE]:
            try:
                try:
                    key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, access_type)
                except:
                    key = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, access_type)

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
    
    try:
        reg_path = r"SOFTWARE\WinRAR\General"
        
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE)
        except:
            key = winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE)
            
        winreg.SetValueEx(key, "ShowLicense", 0, winreg.REG_DWORD, 0)
        winreg.SetValueEx(key, "InstallVersion", 0, winreg.REG_SZ, "6.00") 
        
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
    possible_paths = [
        r"C:\Program Files\WinRAR",
        r"C:\Program Files (x86)\WinRAR",
    ]
    
    for drive in "CDEFGH":
        possible_paths.append(f"{drive}:\\WinRAR")
        possible_paths.append(f"{drive}:\\Program Files\\WinRAR")
        possible_paths.append(f"{drive}:\\Program Files (x86)\\WinRAR")
    
    for path in possible_paths:
        if os.path.exists(path) and os.path.isfile(os.path.join(path, "WinRAR.exe")):
            return path
    
    return None

def check_winrar_installed():
    winrar_path = find_winrar_path()
    if not winrar_path:
        print("[-] WinRAR kurulumu bulunamadı.")
        print("    WinRAR'ı https://www.rarlab.com/download.htm adresinden indirebilirsiniz.")
        return False
    
    print(f"[✓] WinRAR kurulumu bulundu: {winrar_path}")
    return True

def reset_winrar_trial():
    if not QUIET_MODE:
        print("[+] WinRAR deneme süresi sıfırlanıyor...")
    
    try:
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
    if not QUIET_MODE:
        print("[+] Mevcut rarreg.key dosyaları aranıyor...")
    
    found_files = []
    
    drives = ['C:', 'D:', 'E:', 'F:']
    possible_locations = [
        r"\Program Files\WinRAR",
        r"\Program Files (x86)\WinRAR",
        r"\WinRAR",
        r"\Windows",
        r"\Windows\System32"
    ]
    
    for drive in drives:
        for location in possible_locations:
            path = f"{drive}{location}\\rarreg.key"
            if os.path.exists(path):
                found_files.append(path)
    
    users_dir = os.path.join(os.environ.get('SystemDrive', 'C:'), 'Users')
    if os.path.exists(users_dir):
        for user_dir in os.listdir(users_dir):
            appdata_path = os.path.join(users_dir, user_dir, 'AppData')
            if os.path.exists(appdata_path):
                rarreg_path = os.path.join(appdata_path, 'Roaming', 'WinRAR', 'rarreg.key')
                if os.path.exists(rarreg_path):
                    found_files.append(rarreg_path)
                rarreg_path = os.path.join(appdata_path, 'Local', 'WinRAR', 'rarreg.key')
                if os.path.exists(rarreg_path):
                    found_files.append(rarreg_path)
    
    deleted_count = 0
    for file_path in found_files:
        try:
            os.chmod(file_path, 0o777) 
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
    time.sleep(1)
    
    return True

def print_ascii_logo():
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
    if not platform.system() == "Windows":
        print(f"[-] Bu program sadece Windows işletim sistemlerinde çalışır.")
        print(f"    Mevcut işletim sistemi: {platform.system()}")
        return False
    
    return True

def is_discord_running():
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Discord.exe", "/NH"], 
            capture_output=True, 
            text=True, 
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        return "Discord.exe" in result.stdout
    except Exception:
        return False

def open_discord_server():
    print("\n[+] Discord sunucumuza katılmak ister misiniz? (E/H): ", end="")
    choice = input().strip().lower()
    
    if choice == 'e' or choice == 'evet':
        discord_invite_url = "https://discord.gg/codejs"
        discord_app_url = "discord://discord.gg/codejs"
        
        try:
            if is_discord_running():
                print("[+] Discord uygulaması üzerinden sunucuya yönlendiriliyorsunuz...")
                webbrowser.open(discord_app_url)
            else:
                print("[+] Tarayıcı üzerinden Discord sunucusuna yönlendiriliyorsunuz...")
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
    os.system("")
    
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print_ascii_logo()
    
    print("WinRAR aktivatoru baslatiliyor...")
    print()
    
    if not check_os():
        input("\nÇıkmak için bir tuşa basın...")
        sys.exit(1)
    
    if not check_python_version():
        input("\nÇıkmak için bir tuşa basın...")
        sys.exit(1)

    if not is_admin():
        print("[-] Bu aktivatörün düzgün çalışması için admin hakları gerekli!")
        print("    Lütfen bu scripti admin olarak çalıştırın...")
        
        if sys.platform == 'win32':
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        
        input("\nÇıkmak için bir tuşa basın...")
        sys.exit(1)
    
    if not check_winrar_installed():
        input("\nÇıkmak için bir tuşa basın...")
        sys.exit(1)
    
    print("\n[+] AKTIVATOR BASLATILIYOR!")
    print("="*50)
    print("\n[!] LUTFEN BEKLEYIN! Bu islem biraz zaman alabilir...")
    
    force_kill_processes()
    delete_existing_rarreg()
    reset_winrar_trial()
    license_success = create_license_key()
    registry_success = modify_registry()
    
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
    
    open_discord_server()
    
    input("\nÇıkmak için bir tuşa basın...")

if __name__ == "__main__":
    main() 