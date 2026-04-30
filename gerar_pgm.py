import os
from PIL import Image

# Função auxliar que converte imagens em qualquer formato e dimensão para PGM 89x89
# So é necessário se estatuas_pgm estiver vazia 
def converter_para_pgm_p2(caminho_entrada, caminho_saida):
    """
    Abre uma imagem qualquer, converte para tons de cinza, FORÇA O REDIMENSIONAMENTO
    PARA 89x89 (requisito embarcado) e salva como PGM P2 (ASCII).
    """
    try:
        # Abre a imagem, converte para tons de cinza (Luminance) e FAZ O RESIZE
        img = Image.open(caminho_entrada).convert('L').resize((89, 89))
        largura, altura = img.size
        pixels = list(img.getdata())

        with open(caminho_saida, 'w') as f:
            # Cabeçalho PGM P2 padrão
            f.write("P2\n")
            f.write(f"# Convertido de {os.path.basename(caminho_entrada)} (Resized 89x89)\n")
            f.write(f"{largura} {altura}\n")
            f.write("255\n")

            # Escreve os pixels fileira por fileira
            for i in range(0, len(pixels), largura):
                linha = pixels[i:i + largura]
                f.write(" ".join(map(str, linha)) + "\n")

        print(f"  [OK] {os.path.basename(caminho_entrada)} -> {os.path.basename(caminho_saida)} (89x89)")
        return True

    except Exception as e:
        print(f"  [ERRO] Falha ao converter {os.path.basename(caminho_entrada)}: {e}")
        return False

def processar_diretorio(dir_in="estatuas_originais", dir_out="estatuas_pgm"):
    """
    Escaneia o diretório de entrada e converte todas as imagens para o diretório de saída.
    """
    print(f"🔍 Escaneando diretório '{dir_in}' e forçando 89x89...")

    if not os.path.exists(dir_in):
        print(f"❌ Erro: O diretório '{dir_in}' não existe. Crie a pasta e coloque as imagens originais nela.")
        return

    # Cria a pasta de saída se não existir
    if not os.path.exists(dir_out):
        os.makedirs(dir_out)

    # Pega todos os arquivos no diretório de entrada
    arquivos = [f for f in os.listdir(dir_in) if os.path.isfile(os.path.join(dir_in, f))]

    if not arquivos:
        print(f"⚠️ Nenhuma imagem encontrada em '{dir_in}'.")
        return

    print(f"Encontrados {len(arquivos)} arquivos. Iniciando conversão para PGM P2...\n")

    sucessos = 0
    for arquivo in arquivos:
        caminho_in = os.path.join(dir_in, arquivo)

        # Troca a extensão original por .pgm
        nome_sem_extensao = os.path.splitext(arquivo)[0]
        caminho_out = os.path.join(dir_out, f"{nome_sem_extensao}.pgm")

        if converter_para_pgm_p2(caminho_in, caminho_out):
            sucessos += 1

    print(f"\n✅ Conversão concluída! {sucessos}/{len(arquivos)} arquivos prontos em '{dir_out}'.")


# --- Execução ---
if __name__ == "__main__":
    processar_diretorio()
