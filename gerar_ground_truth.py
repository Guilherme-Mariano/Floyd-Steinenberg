import os
from PIL import Image

# Script auxiliar para gerar o ground truth ( gabarito para testes )

def gerar_ground_truth_pillow(caminho_in, caminho_out):
    """
    Gera a imagem de referência usando o algoritmo Floyd-Steinberg
    do Pillow e salva estritamente como PGM P2 (ASCII).
    """
    try:
        # Abre a imagem PGM original em tons de cinza e GARANTE 89x89
        img = Image.open(caminho_in).convert('L').resize((89, 89))

        # Aplica o dithering Floyd-Steinberg nativo do Pillow
        img_dithered = img.convert('1', dither=Image.FLOYDSTEINBERG)

        largura, altura = img_dithered.size
        pixels_1bit = list(img_dithered.getdata())

        # Salva manualmente como PGM P2 para bater exatamente com a leitura da sua auditoria
        with open(caminho_out, 'w') as f:
            f.write("P2\n")
            f.write(f"# Ground Truth gerado via Pillow (89x89)\n")
            f.write(f"{largura} {altura}\n")
            f.write("255\n")

            for i in range(0, len(pixels_1bit), largura):
                linha = pixels_1bit[i:i + largura]
                # Converte o 1-bit do Pillow (0 ou 255) para a string correta
                linha_formatada = ["255" if p > 0 else "0" for p in linha]
                f.write(" ".join(linha_formatada) + "\n")

        return True
    except Exception as e:
        print(f"Erro ao processar {os.path.basename(caminho_in)}: {e}")
        return False

def processar_ground_truth(dir_in="estatuas_pgm", dir_out="estatuas_pillow"):
    print(f"🐍 Iniciando geração de Ground Truth (Pillow) garantindo 89x89...")

    if not os.path.exists(dir_in):
        print(f"❌ Erro: O diretório '{dir_in}' não existe.")
        return

    if not os.path.exists(dir_out):
        os.makedirs(dir_out)

    arquivos_pgm = [f for f in os.listdir(dir_in) if f.endswith(".pgm")]

    if not arquivos_pgm:
        print(f"⚠️ Nenhuma imagem encontrada em '{dir_in}'.")
        return

    print(f"Processando {len(arquivos_pgm)} imagens...\n")

    sucessos = 0
    for arquivo in arquivos_pgm:
        caminho_in = os.path.join(dir_in, arquivo)
        caminho_out = os.path.join(dir_out, f"pillow_{arquivo}")

        if gerar_ground_truth_pillow(caminho_in, caminho_out):
            print(f"  [OK] Gerado: pillow_{arquivo}")
            sucessos += 1

    print(f"\n✅ Geração concluída! {sucessos} arquivos de referência salvos em '{dir_out}'.")


if __name__ == "__main__":
    processar_ground_truth()
