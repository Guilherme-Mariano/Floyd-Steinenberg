import os
import sys
import math
import csv
import warnings
import time
import serial
from PIL import Image, ImageFilter

# Suprime os avisos futuros do Pillow para manter o terminal limpo na apresentação
warnings.filterwarnings("ignore", category=DeprecationWarning)

# --- CONFIGURAÇÕES DO AMBIENTE ---
DIR_ORIG = "estatuas_pgm"
DIR_UART = "estatuas_saida_uart" # Diretório atualizado para a saída da serial
DIR_PILLOW = "estatuas_pillow"
NOME_CSV_SAIDA = "relatorio_auditoria.csv"

# --- CONFIGURAÇÕES DA PORTA SERIAL ---
PORT = 'COM7'  # Altere conforme necessário para a sua porta
BAUDRATE = 115200


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
        erro_percentual = (mse_perceptual / 65025.0) * 100.0
        similaridade_perceptual = 100.0 - erro_percentual

        return similaridade_perceptual

    except Exception as e:
        print(f"Erro no cálculo HVS para {caminho_orig}: {e}")
        return None


def processar_imagem_via_uart(caminho_in, caminho_out, ser):
    """Lê o arquivo, divide ao meio dinamicamente, envia via serial e salva o PGM retornado."""
    with open(caminho_in, 'r') as f:
        conteudo = f.read()

    # Limpeza de comentários e formatação
    linhas = conteudo.split('\n')
    linhas_limpas = [linha.split('#')[0] for linha in linhas]
    texto_sem_comentarios = ' '.join(linhas_limpas)
    tokens = texto_sem_comentarios.split()

    if tokens[0] != 'P2':
        raise ValueError(f"Arquivo {caminho_in} não é um PGM ASCII (P2).")

    largura = int(tokens[1])
    altura = int(tokens[2])
    max_val = int(tokens[3])
    
    # Prepara o bytearray de pixels
    pixels = bytearray(int(p) for p in tokens[4:])
    total_pixels = largura * altura

    if len(pixels) < total_pixels:
        print(f"[AVISO] {caminho_in} tem menos pixels ({len(pixels)}) que o esperado ({total_pixels}).")

    # Calcula a divisão dinamicamente (garante que funciona para outros tamanhos além de 89x89)
    linhas_metade_1 = (altura // 2) + (altura % 2)
    bytes_metade_1 = linhas_metade_1 * largura
    
    part1 = pixels[:bytes_metade_1]
    part2 = pixels[bytes_metade_1:]
    resultado_final = []

    # ================= ENVIO PARTE 1 =================
    while True:
        linha = ser.readline().decode('utf-8', errors='ignore').strip()
        if "Esperando Parte 1" in linha:
            break

    time.sleep(0.1)
    ser.write(b'\xAA') # START_PART1
    time.sleep(0.01)
    ser.write(part1)
    time.sleep(0.01)
    ser.write(b'\x55') # END_BYTE

    while True:
        linha = ser.readline().decode('utf-8', errors='ignore').strip()
        if linha == "FIM_CHUNK":
            break
        elif linha == "0" or linha == "255":
            resultado_final.append(linha)

    # ================= ENVIO PARTE 2 =================
    while True:
        linha = ser.readline().decode('utf-8', errors='ignore').strip()
        if "Esperando Parte 2" in linha:
            break

    time.sleep(0.1)
    ser.write(b'\xBB') # START_PART2
    time.sleep(0.01)
    ser.write(part2)
    time.sleep(0.01)
    ser.write(b'\x55') # END_BYTE

    while True:
        linha = ser.readline().decode('utf-8', errors='ignore').strip()
        if linha == "FIM_CHUNK":
            break
        elif linha == "0" or linha == "255":
            resultado_final.append(linha)

    # ================= SALVAR RESULTADO =================
    with open(caminho_out, "w") as f:
        f.write("P2\n")
        f.write(f"# Processado via UART ({PORT}) - Dithering Metade-Metade\n")
        f.write(f"{largura} {altura}\n")
        f.write("255\n")
        
        for i, val in enumerate(resultado_final):
            f.write(val + " ")
            if (i + 1) % largura == 0:
                f.write("\n")


def main():
    # 1. PREPARAÇÃO DO AMBIENTE E SERIAL
    print("=" * 60)
    print(f"🚀 [1/4] INICIALIZANDO COMUNICAÇÃO SERIAL NA {PORT}")
    print("=" * 60)
    
    if not os.path.exists(DIR_ORIG):
        print(f"❌ Erro: Pasta '{DIR_ORIG}' não encontrada.")
        sys.exit(1)
    if not os.path.exists(DIR_UART): 
        os.makedirs(DIR_UART)

    arquivos_pgm = [f for f in os.listdir(DIR_ORIG) if f.endswith(".pgm")]
    
    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=1)
        time.sleep(2) # Tempo para estabilização do hardware
        print("✅ Porta serial aberta com sucesso!\n")
    except serial.SerialException as e:
        print(f"❌ ERRO AO ABRIR PORTA SERIAL:\n{e}")
        sys.exit(1)

    # 2. EXECUÇÃO EM LOTE VIA UART
    print(f"⚙️ [2/4] PROCESSANDO {len(arquivos_pgm)} IMAGENS VIA UART (STM32)...")

    ultimo_arquivo = None
    try:
        for arquivo in arquivos_pgm:
            caminho_in = f"{DIR_ORIG}/{arquivo}"
            caminho_out = f"{DIR_UART}/dithered_{arquivo}"
            
            print(f"  [>] Enviando '{arquivo}' para processamento...")
            try:
                processar_imagem_via_uart(caminho_in, caminho_out, ser)
                print(f"  [OK] Retorno processado: dithered_{arquivo}")
                ultimo_arquivo = caminho_out
            except Exception as ex_arquivo:
                print(f"  [ERRO] Falha no arquivo {arquivo}: {ex_arquivo}")
                
    finally:
        # Garante que a porta serial seja sempre fechada
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("\n🔒 Porta serial fechada.")

    # 3. AUDITORIA (TESTES DE VALIDAÇÃO E EXPORTAÇÃO CSV)
    print("\n" + "=" * 60)
    print(f"{'🔬 [3/4] LAUDO DE AUDITORIA CONSOLIDADO':^60}")
    print("=" * 60)

    # Variáveis para cálculo das médias globais
    soma_sim_byte = 0
    soma_sim_hvs_uart = 0
    soma_cons_uart = 0
    soma_cons_pil = 0
    qtd_sucesso = 0

    with open(NOME_CSV_SAIDA, mode='w', newline='', encoding='utf-8') as arquivo_csv:
        escritor_csv = csv.writer(arquivo_csv)
        escritor_csv.writerow(['Arquivo', 'Similaridade_Byte_a_Byte(UART_vs_Pil_%)', 'Similaridade_HVS_%(Orig_vs_UART)', 'Energia_UART(%)', 'Energia_Pillow(%)'])

        for arquivo in arquivos_pgm:
            caminho_orig = os.path.join(DIR_ORIG, arquivo)
            caminho_uart = os.path.join(DIR_UART, f"dithered_{arquivo}")
            caminho_pil = os.path.join(DIR_PILLOW, f"pillow_{arquivo}")

            if not os.path.exists(caminho_uart) or not os.path.exists(caminho_pil):
                continue

            try:
                px_orig = ler_payload_pgm(caminho_orig)
                px_uart = ler_payload_pgm(caminho_uart)
                px_pil = ler_payload_pgm(caminho_pil)
                n = len(px_orig)

                iguais = sum(1 for u, p in zip(px_uart, px_pil) if u == p)
                sim_byte = (iguais / n) * 100

                sim_hvs_uart = calcular_similaridade_perceptual(caminho_orig, caminho_uart)

                media_orig = sum(px_orig) / n
                media_uart = sum(px_uart) / n
                media_pil = sum(px_pil) / n

                cons_uart = 100 - (abs(media_orig - media_uart) / 255 * 100)
                cons_pil = 100 - (abs(media_orig - media_pil) / 255 * 100)

                escritor_csv.writerow([
                    arquivo,
                    f"{sim_byte:.2f}",
                    f"{sim_hvs_uart:.2f}" if sim_hvs_uart is not None else "ERRO",
                    f"{cons_uart:.2f}",
                    f"{cons_pil:.2f}"
                ])

                if sim_hvs_uart is not None:
                    soma_sim_byte += sim_byte
                    soma_sim_hvs_uart += sim_hvs_uart
                    soma_cons_uart += cons_uart
                    soma_cons_pil += cons_pil
                    qtd_sucesso += 1

            except Exception as e:
                print(f"⚠️ Erro ao processar métricas de {arquivo}: {e}")

    # Exibe as métricas consolidadas no terminal
    if qtd_sucesso > 0:
        media_sim_byte = soma_sim_byte / qtd_sucesso
        media_sim_hvs_uart = soma_sim_hvs_uart / qtd_sucesso
        media_cons_uart = soma_cons_uart / qtd_sucesso
        media_cons_pil = soma_cons_pil / qtd_sucesso

        print(f"✅ Resultados individuais salvos em: {NOME_CSV_SAIDA}")
        print("\n📊 MÉDIAS GLOBAIS DO DATASET:")
        print(f"   ➤ Imagens avaliadas     : {qtd_sucesso}")
        print(f"   ➤ Similaridade Byte (%) : {media_sim_byte:.2f}%")
        print(f"   ➤ Similaridade HVS (%)  : {media_sim_hvs_uart:.2f}%")
        print(f"   ➤ Energia retida UART(%): {media_cons_uart:.2f}%")
        print(f"   ➤ Energia retida Pil (%): {media_cons_pil:.2f}%")
    else:
        print("❌ Nenhuma imagem pôde ser validada com sucesso.")

    print("=" * 60)

    # 4. VISUALIZAÇÃO FINAL
    if ultimo_arquivo:
        visualizar_pgm_no_terminal(ultimo_arquivo)


if __name__ == "__main__":
    main()
