import subprocess
import os
import sys
import math
import csv
import warnings
from PIL import Image, ImageFilter

# Suprime os avisos futuros do Pillow para manter o terminal limpo na apresentação
warnings.filterwarnings("ignore", category=DeprecationWarning)

# --- CONFIGURAÇÕES DO AMBIENTE ---
DIR_ORIG = "estatuas_pgm"
DIR_C = "estatuas_saida_c"
DIR_PILLOW = "estatuas_pillow"
NOME_CODIGO_C = "main.c"
NOME_EXECUTAVEL = "processar_imagem"
NOME_CSV_SAIDA = "relatorio_auditoria.csv"


def visualizar_pgm_no_terminal(caminho_arquivo):
    """Gera uma visualização ASCII rápida da imagem no terminal."""
    try:
        with open(caminho_arquivo, 'r') as f:
            tokens = [palavra for linha in f for palavra in linha.split('#')[0].split()]

        if not tokens or tokens[0] != 'P2':
            return

        w, h = int(tokens[1]), int(tokens[2])
        pixels = [int(p) for p in tokens[4:]]

        print(f"\n--- PREVIEW DA SAÍDA ({w}x{h}) ---")
        caracteres_ascii = "@%#*+=-:. "

        for y in range(h):
            linha_texto = ""
            for x in range(w):
                pixel_val = pixels[y * w + x]
                idx = int((pixel_val / 255) * (len(caracteres_ascii) - 1))
                linha_texto += caracteres_ascii[idx] * 2
            print(linha_texto)
        print("-" * 40 + "\n")
    except Exception as e:
        print(f"Erro ao visualizar: {e}")


def ler_payload_pgm(caminho_arq):
    """Lê o payload P2 e retorna lista de pixels inteiros."""
    tokens = []
    with open(caminho_arq, 'r', encoding='ascii', errors='ignore') as f:
        for linha in f:
            linha_sem_comentario = linha.split('#')[0].strip()
            if not linha_sem_comentario: continue
            tokens.extend(linha_sem_comentario.split())
    if len(tokens) > 4 and tokens[0] == 'P2':
        return [int(x) for x in tokens[4:]]
    raise ValueError(f"Arquivo {caminho_arq} inválido.")


def calcular_similaridade_perceptual(caminho_orig, caminho_dither):
    """
    Simula o Sistema Visual Humano (HVS) aplicando um Filtro Passa-Baixa
    antes de calcular o erro entre a imagem original e o dithering.
    """
    try:
        # Abre as imagens
        img_orig = Image.open(caminho_orig).convert('L')
        img_dither = Image.open(caminho_dither).convert('L')

        # Aplica o Filtro Passa-Baixa (Desfoque Gaussiano com raio 2)
        # Isso simula a integração espacial que a retina humana faz
        blur_orig = img_orig.filter(ImageFilter.GaussianBlur(radius=2))
        blur_dither = img_dither.filter(ImageFilter.GaussianBlur(radius=2))

        pixels_orig = list(blur_orig.getdata())
        pixels_dither = list(blur_dither.getdata())

        tamanho = len(pixels_orig)
        soma_erros_quadrados = 0

        # Calcula o Erro Perceptual
        for po, pd in zip(pixels_orig, pixels_dither):
            soma_erros_quadrados += (po - pd) ** 2

        mse_perceptual = soma_erros_quadrados / tamanho

        # Converte o erro em uma porcentagem de similaridade (0 a 100%)
        # O erro máximo possível ao quadrado é 255^2 (65025)
        erro_percentual = (mse_perceptual / 65025.0) * 100.0
        similaridade_perceptual = 100.0 - erro_percentual

        return similaridade_perceptual

    except Exception as e:
        print(f"Erro no cálculo HVS para {caminho_orig}: {e}")
        return None


def main():
    # 1. COMPILAÇÃO
    print("=" * 60)
    print(f"🚀 [1/4] COMPILANDO: {NOME_CODIGO_C}")
    print("=" * 60)
    compilacao = subprocess.run(
        ["wsl", "gcc", "-O3", NOME_CODIGO_C, "-o", NOME_EXECUTAVEL],
        capture_output=True, text=True
    )
    if compilacao.returncode != 0:
        print(f"❌ ERRO NO GCC:\n{compilacao.stderr}")
        sys.exit(1)
    print("✅ Compilação bem-sucedida!\n")

    # 2. EXECUÇÃO EM LOTE
    if not os.path.exists(DIR_ORIG):
        print(f"❌ Erro: Pasta {DIR_ORIG} não encontrada.")
        sys.exit(1)
    if not os.path.exists(DIR_C): os.makedirs(DIR_C)

    arquivos_pgm = [f for f in os.listdir(DIR_ORIG) if f.endswith(".pgm")]
    print(f"⚙️ [2/4] PROCESSANDO {len(arquivos_pgm)} IMAGENS VIA C...")

    ultimo_arquivo = None
    for arquivo in arquivos_pgm:
        caminho_in = f"{DIR_ORIG}/{arquivo}"
        caminho_out = f"{DIR_C}/dithered_{arquivo}"

        exec_c = subprocess.run(
            ["wsl", f"./{NOME_EXECUTAVEL}", caminho_in, caminho_out],
            capture_output=True, text=True
        )
        if exec_c.returncode == 0:
            print(f"  [OK] {arquivo}")
            ultimo_arquivo = caminho_out
        else:
            print(f"  [ERRO] {arquivo}: {exec_c.stderr.strip()}")

    # 3. AUDITORIA (TESTES DE VALIDAÇÃO E EXPORTAÇÃO CSV)
    print("\n" + "=" * 60)
    print(f"{'🔬 [3/4] LAUDO DE AUDITORIA CONSOLIDADO':^60}")
    print("=" * 60)

    # Variáveis para cálculo das médias globais
    soma_sim_byte = 0
    soma_sim_hvs_c = 0
    soma_cons_c = 0
    soma_cons_pil = 0
    qtd_sucesso = 0

    # Abre o arquivo CSV para escrita
    with open(NOME_CSV_SAIDA, mode='w', newline='', encoding='utf-8') as arquivo_csv:
        escritor_csv = csv.writer(arquivo_csv)
        # Escreve o cabeçalho no CSV
        escritor_csv.writerow(['Arquivo', 'Similaridade_Byte_a_Byte(C_vs_Pil_%)', 'Similaridade_HVS_%(Orig_vs_C)', 'Energia_C(%)', 'Energia_Pillow(%)'])

        for arquivo in arquivos_pgm:
            caminho_orig = os.path.join(DIR_ORIG, arquivo)
            caminho_c = os.path.join(DIR_C, f"dithered_{arquivo}")
            caminho_pil = os.path.join(DIR_PILLOW, f"pillow_{arquivo}")

            if not os.path.exists(caminho_c) or not os.path.exists(caminho_pil):
                continue

            try:
                # Carrega as matrizes cruas para as métricas exatas
                px_orig = ler_payload_pgm(caminho_orig)
                px_c = ler_payload_pgm(caminho_c)
                px_pil = ler_payload_pgm(caminho_pil)
                n = len(px_orig)

                # METRICA 1: Similaridade Byte-a-Byte (C vs Pillow)
                iguais = sum(1 for c, p in zip(px_c, px_pil) if c == p)
                sim_byte = (iguais / n) * 100

                # METRICA 2: Similaridade Perceptual HVS (usando a sua função com Filtro Passa-Baixa)
                sim_hvs_c = calcular_similaridade_perceptual(caminho_orig, caminho_c)

                # METRICA 3: Conservação de Energia
                media_orig = sum(px_orig) / n
                media_c = sum(px_c) / n
                media_pil = sum(px_pil) / n

                cons_c = 100 - (abs(media_orig - media_c) / 255 * 100)
                cons_pil = 100 - (abs(media_orig - media_pil) / 255 * 100)

                # Salva os dados individuais no CSV
                escritor_csv.writerow([
                    arquivo,
                    f"{sim_byte:.2f}",
                    f"{sim_hvs_c:.2f}" if sim_hvs_c is not None else "ERRO",
                    f"{cons_c:.2f}",
                    f"{cons_pil:.2f}"
                ])

                # Acumula para as médias globais
                if sim_hvs_c is not None:
                    soma_sim_byte += sim_byte
                    soma_sim_hvs_c += sim_hvs_c
                    soma_cons_c += cons_c
                    soma_cons_pil += cons_pil
                    qtd_sucesso += 1

            except Exception as e:
                print(f"⚠️ Erro ao processar métricas de {arquivo}: {e}")

    # Exibe as métricas consolidadas no terminal
    if qtd_sucesso > 0:
        media_sim_byte = soma_sim_byte / qtd_sucesso
        media_sim_hvs_c = soma_sim_hvs_c / qtd_sucesso
        media_cons_c = soma_cons_c / qtd_sucesso
        media_cons_pil = soma_cons_pil / qtd_sucesso

        print(f"✅ Resultados individuais salvos em: {NOME_CSV_SAIDA}")
        print("\n📊 MÉDIAS GLOBAIS DO DATASET:")
        print(f"   ➤ Imagens avaliadas     : {qtd_sucesso}")
        print(f"   ➤ Similaridade Byte (%) : {media_sim_byte:.2f}%")
        print(f"   ➤ Similaridade HVS (%)  : {media_sim_hvs_c:.2f}%")
        print(f"   ➤ Energia retida C (%)  : {media_cons_c:.2f}%")
        print(f"   ➤ Energia retida Pil (%) : {media_cons_pil:.2f}%")
    else:
        print("❌ Nenhuma imagem pôde ser validada com sucesso.")

    print("=" * 60)

    # 4. VISUALIZAÇÃO FINAL
    if ultimo_arquivo:
        visualizar_pgm_no_terminal(ultimo_arquivo)


if __name__ == "__main__":
    main()