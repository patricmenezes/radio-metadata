import os 
import json
import difflib
from ftplib import FTP, error_perm
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from PIL import Image
from io import BytesIO

# Configurações locais
JAZLER_METADATA_FILE = r"C:\\Jazler RadioStar 2\\Exports\\NowOnAir.txt"
MUSIC_FOLDER = r"C:\\P\\MUSICAS"

# Configurações do FTP


# URL base para as capas
COVER_URL_BASE = "https://popfi.online/public_html/covers/"

def ler_nome_musica():
    """Lê o nome da música atual do arquivo do Jazler."""
    try:
        with open(JAZLER_METADATA_FILE, "r", encoding="ISO-8859-1", errors="ignore") as f:
            linha = f.readline().strip()
        if "Now On Air:" in linha:
            return linha.split("Now On Air:")[1].strip()
        return None
    except Exception as e:
        print(f"❌ Erro ao ler arquivo do Jazler: {e}")
        return None

def encontrar_arquivo_musica(nome_musica):
    """Encontra o arquivo MP3 mais parecido com o nome informado."""
    try:
        arquivos_mp3 = [arquivo for arquivo in os.listdir(MUSIC_FOLDER) if arquivo.lower().endswith(".mp3")]
        arquivo_encontrado = difflib.get_close_matches(nome_musica, arquivos_mp3, n=1, cutoff=0.4)
        return os.path.join(MUSIC_FOLDER, arquivo_encontrado[0]) if arquivo_encontrado else None
    except Exception as e:
        print(f"❌ Erro ao buscar música: {e}")
        return None

def extrair_metadados(mp3_file):
    """Extrai título, artista e capa da música."""
    try:
        print(f"🔍 Extraindo metadados de {mp3_file}...")
        audio = MP3(mp3_file, ID3=ID3)

        titulo = audio.tags.get("TIT2", ["Desconhecido"])[0]
        artista = audio.tags.get("TPE1", ["Desconhecido"])[0]
        ano = str(audio.tags.get("TDRC", ["Desconhecido"])[0])[:4]
        capa_nome = f"{artista} - {titulo}.webp".replace("/", "_").replace("\\", "_")
        
        for tag in audio.tags.values():
            if isinstance(tag, APIC):
                img = Image.open(BytesIO(tag.data)).convert("RGB").resize((400, 400))
                output = BytesIO()
                img.save(output, format="WEBP", quality=85, optimize=True)
                return {
                    "titulo": titulo,
                    "artista": artista,
                    "ano": ano,
                    "capa_nome": capa_nome,
                    "capa_data": output.getvalue(),
                    "capa_url": f"{COVER_URL_BASE}{capa_nome}"
                }
        
        return {"titulo": titulo, "artista": artista, "ano": ano, "capa_nome": None, "capa_data": None, "capa_url": None}
    except Exception as e:
        print(f"❌ Erro ao extrair metadados: {e}")
        return None

def enviar_para_ftp(ftp, arquivo_nome, arquivo_data, diretorio):
    """Envia arquivos para o FTP, garantindo que o diretório exista."""
    try:
        try:
            ftp.cwd(diretorio)
        except error_perm:
            print(f"📂 Criando diretório {diretorio} no FTP...")
            ftp.mkd(diretorio)
            ftp.cwd(diretorio)
        
        with BytesIO(arquivo_data) as f:
            ftp.storbinary(f"STOR {arquivo_nome}", f)
        print(f"✅ {arquivo_nome} enviado para {diretorio}")
    except Exception as e:
        print(f"❌ Erro ao enviar {arquivo_nome} via FTP: {e}")

def main():
    """Processo principal para capturar metadados e enviá-los ao FTP."""
    print("🎬 Iniciando processo...")
    
    nome_musica = ler_nome_musica()
    if not nome_musica:
        print("❌ Nenhuma música em reprodução encontrada.")
        return

    print(f"🎵 Música atual: {nome_musica}")
    caminho_musica = encontrar_arquivo_musica(nome_musica)
    if not caminho_musica:
        print("⚠️ Nenhum arquivo MP3 correspondente encontrado.")
        return

    metadata = extrair_metadados(caminho_musica)
    if not metadata:
        return

    with FTP() as ftp:
        ftp.connect(FTP_HOST, FTP_PORT)
        ftp.login(FTP_USER, FTP_PASS)

        if metadata["capa_data"]:
            enviar_para_ftp(ftp, metadata["capa_nome"], metadata["capa_data"], FTP_COVERS_DIR)

        json_data = {
            "detalhado": {
                "titulo": metadata["titulo"],
                "artista": metadata["artista"],
                "album": metadata.get("album", "Desconhecido"),
                "ano": metadata["ano"],
                "capa": metadata["capa_url"]
            },
            "simples": {
                "titulo": metadata["titulo"],
                "artista": metadata["artista"],
                "capa": metadata["capa_url"]
            }
        }
        json_bytes = json.dumps(json_data, ensure_ascii=False, indent=4).encode("utf-8")
        enviar_para_ftp(ftp, "nowplaying.json", json_bytes, FTP_JSON_DIR)

    print("✅ Processo concluído!")

if __name__ == "__main__":
    main()
