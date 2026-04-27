#include <stdio.h>
#include <stdlib.h>



#define IMG_W 89
#define IMG_H 89

static unsigned char img_buffer[IMG_W * IMG_H];
static short errors[IMG_W + 1];

#define CLIP8(v) ((v) <= 0 ? 0 : ((v) >= 255 ? 255 : (v)))

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
