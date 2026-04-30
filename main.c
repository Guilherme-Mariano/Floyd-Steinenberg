/*
 * ------------------------------------------------------------
 * Nome: Processador de Imagem PGM com Dithering Floyd-Steinberg
 *
 * Descrição:
 * Este programa lê uma imagem no formato PGM (P2 - ASCII),
 * aplica o algoritmo de dithering de Floyd-Steinberg e gera
 * uma imagem binarizada (preto e branco).
 *
 * Uso:
 * ./processar_imagem entrada.pgm saida.pgm
 *
 * Entrada:
 * - Arquivo PGM (P2 ASCII), 89x89, valores de 0 a 255
 *
 * Saída:
 * - Arquivo PGM (P2 ASCII), binarizado (0 ou 255)
 *
 * Autor(es):
 * Guilherme Mariano Freire Bezerra
 * Laura Kida
 *
 * Data:
 * Abril de 2026
 *
 * Contexto:
 * Trabalho acadêmico - processamento de imagens / sistemas embarcados
 *
 * Plataforma alvo:
 * Simulação desktop / possível adaptação para embarcados
 */


#include <stdio.h>
#include <stdlib.h>



#define IMG_W 89
#define IMG_H 89

// Estamos usando unsigned char ( o resultado prático é uma variável menor que o int sugerido nas especificações )
// O uso do unsigned foi mantido pelo fato de que a precisão não foi afetada de forma alguma
// O uso do unsigned permitiu grande economia apesar de ficar bem abaixo do limiar estabelicido de 8k de memória
// Unsigned char se encaixa perfeitamente para o nosso caso, pois ele tem valor de 1byte ( 8bits ) 0 a 255
/*
 * Buffer da imagem em escala de cinza.
 * Tamanho fixo: 89x89 pixels.
 * Cada pixel varia de 0 a 255.
 */
static unsigned char img_buffer[IMG_W * IMG_H];
// Aqui declara-se o vetor de erros, estamos usando o tipo short ( apesar de haver a possibilidade de usar o tipo int )
// Mantivemos o vetor desse tipo pelo fato de que não seria necessário armazenar erros maiores que 255 ou menores que -255
// No caso Short é metade do tamanho da int ( 2bytes vs 4bytes )
/*
 * Vetor auxiliar para propagação de erro do algoritmo.
 * Armazena erros acumulados por coluna.
 */
static short errors[IMG_W + 1];
// Essa é uma linha importante para evitar repetir código mais a frente. 
// O uso desse macro nos permite definir os boundaries dos valores possíveis para nossos pixels
#define CLIP8(v) ((v) <= 0 ? 0 : ((v) >= 255 ? 255 : (v)))
// Aqui está a função importante
// Ela foi modularizada para se comportar de forma independente ( Como neste código estamos usando fin fout, se estivessemos
// em um embarcado lendo de uma porta serial ela não seria afetada
/*
 * Função: apply_floyd_steinberg
 *
 * Descrição:
 * Aplica o algoritmo de dithering de Floyd-Steinberg
 * sobre o buffer global de imagem.
 *
 * Parâmetros:
 * - width: largura da imagem
 * - height: altura da imagem
 *
 * Retorno:
 * - void
 *
 * Efeitos colaterais:
 * - Modifica o vetor global img_buffer
 * - Utiliza e altera o vetor global errors
 */
static void apply_floyd_steinberg(int width, int height) {
    int x, y;

    for (x = 0; x <= width; x++) {
        errors[x] = 0;
    }

    for (y = 0; y < height; y++) {
        int l, l0, l1, l2, d2;
        unsigned char *row = &img_buffer[y * width];
        unsigned char outv;

        l = 0;
        l0 = 0;
        l1 = 0;

        for (x = 0; x < width; x++) {
            // Estamos dando um cast (int) do pixel que estava em formato unsigned char
            // Ele sera adicionado ao erro fracionado ( esse erro pode ser negativo )
            l = CLIP8((int)row[x] + (l + (int)errors[x + 1]) / 16);
            outv = (l > 128) ? 255 : 0;
            row[x] = outv;

            l -= (int)outv;
            l2 = l;
            d2 = l + l;
            l += d2;
            errors[x] = (short)(l + l0);
            l += d2;
            l0 = l + l1;
            l1 = l2;
            l += d2;
        }
        errors[x] = (short)l0;
    }
}

// Função auxiliar para elimnar possíveis comentarios no PGM
/*
 * Função: pular_comentarios
 *
 * Descrição:
 * Ignora comentários e espaços em branco no arquivo PGM.
 *
 * Parâmetros:
 * - f: ponteiro para arquivo aberto
 *
 * Retorno:
 * - void
 *
 * Efeitos colaterais:
 * - Avança o cursor do arquivo
 */
static void pular_comentarios(FILE *f) {
    int ch;
    while ((ch = fgetc(f)) != EOF) {
        if (ch == '#') {
            while ((ch = fgetc(f)) != '\n' && ch != EOF);
        } else if (ch != ' ' && ch != '\t' && ch != '\n' && ch != '\r') {
            ungetc(ch, f);
            break;
        }
    }
}

// Função MAIN, tratando de ler os arquivos e chamar as rotinas
int main(int argc, char *argv[]) {
    FILE *fin, *fout;
    char p2[3];
    int width, height, max_val, i, v;

    if (argc != 3) {
        printf("Uso: ./processar_imagem <arquivo_entrada.pgm> <arquivo_saida.pgm>\n");
        return 1;
    }

    fin = fopen(argv[1], "r");
    if (fin == NULL) {
        printf("Erro ao abrir %s\n", argv[1]);
        return 1;
    }

    fscanf(fin, "%2s", p2);
    if (p2[0] != 'P' || p2[1] != '2') {
        printf("Erro: %s nao eh PGM ASCII (P2).\n", argv[1]);
        fclose(fin);
        return 1;
    }

    pular_comentarios(fin);
    fscanf(fin, "%d %d", &width, &height);

    pular_comentarios(fin);
    fscanf(fin, "%d", &max_val);

    if (max_val != 255) {
        printf("Erro: max_val deve ser 255.\n");
        fclose(fin);
        return 1;
    }

    if (width != IMG_W || height != IMG_H) {
        printf("Erro: imagem deve ser %dx%d (recebido %dx%d).\n",
               IMG_W, IMG_H, width, height);
        fclose(fin);
        return 1;
    }

    for (i = 0; i < width * height; i++) {
        pular_comentarios(fin);
        if (fscanf(fin, "%d", &v) != 1) {
            printf("Erro: leitura de pixel %d falhou.\n", i);
            fclose(fin);
            return 1;
        }
        if (v < 0) v = 0;
        if (v > 255) v = 255;
        img_buffer[i] = (unsigned char)v;
    }
    fclose(fin);

    apply_floyd_steinberg(width, height);

    fout = fopen(argv[2], "w");
    if (fout == NULL) {
        printf("Erro ao criar %s.\n", argv[2]);
        return 1;
    }

    fprintf(fout, "P2\n# Processado em C (Embarcado)\n%d %d\n255\n", width, height);

    for (i = 0; i < width * height; i++) {
        fprintf(fout, "%d ", (int)img_buffer[i]);
        if ((i + 1) % width == 0) {
            fprintf(fout, "\n");
        }
    }
    fclose(fout);

    return 0;
}
