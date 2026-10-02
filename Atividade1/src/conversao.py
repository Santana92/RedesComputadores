# ==============================================================================
# Projeto: Camada Física usando Som (Redes de Computadores)
# Licença: MIT Open Source (veja LICENSE na raiz do projeto)
# ==============================================================================

"""
Módulo de Conversão: Mensagem <-> Bytes <-> Bits.

Responsável pela camada de representação e formatação dos dados.
Permite transformar texto em sequências binárias para transmissão
e remontar o texto original a partir dos bits recebidos.
"""

from typing import List


def mensagem_para_bytes(mensagem: str, encoding: str = "utf-8") -> bytes:
    """Converte uma string de texto em uma sequência de bytes."""
    return mensagem.encode(encoding)


def bytes_para_mensagem(dados: bytes, encoding: str = "utf-8") -> str:
    """
    Converte bytes recebidos de volta para texto.
    Usa 'replace' para caracteres inválidos para não quebrar em caso de ruído.
    """
    # Decidimos usar errors='replace' para evitar que o programa trave se algum ruído
    # corromper um byte durante a transmissão acústica.
    return dados.decode(encoding, errors="replace")


def bytes_para_bits(dados: bytes) -> List[int]:
    """
    Converte uma sequência de bytes em uma lista de bits (0s e 1s).
    A ordem utilizada é MSB (bit mais significativo primeiro).
    Exemplo: byte 65 ('A' = 0b01000001) -> [0, 1, 0, 0, 0, 0, 0, 1].
    """
    bits = []
    # Aqui extraímos cada um dos 8 bits do byte, do mais significativo (bit 7)
    # até o menos significativo (bit 0), usando deslocamento para a direita e máscara & 1.
    for b in dados:
        for shift in range(7, -1, -1):
            bit = (b >> shift) & 1
            bits.append(bit)
    return bits


def bits_para_bytes(bits: List[int]) -> bytes:
    """
    Converte uma lista de bits de volta para bytes.
    Agrupa os bits de 8 em 8. Bits excedentes que não formem
    um byte completo são ignorados ou preenchidos.
    """
    byte_list = []
    # Nessa parte agrupamos os bits de 8 em 8 para remontar os bytes originais.
    # Usamos deslocamento para a esquerda (<< 1) e OU binário (|) para acumular os bits.
    for i in range(0, len(bits) - (len(bits) % 8), 8):
        byte_val = 0
        for bit in bits[i : i + 8]:
            byte_val = (byte_val << 1) | (bit & 1)
        byte_list.append(byte_val)
    return bytes(byte_list)


def mensagem_para_bits(mensagem: str, encoding: str = "utf-8") -> List[int]:
    """Atalho para converter diretamente texto em lista de bits."""
    return bytes_para_bits(mensagem_para_bytes(mensagem, encoding))


def bits_para_mensagem(bits: List[int], encoding: str = "utf-8") -> str:
    """Atalho para converter diretamente lista de bits em texto."""
    return bytes_para_mensagem(bits_para_bytes(bits), encoding)


def formatar_bits(bits: List[int], agrupamento: int = 8) -> str:
    """
    Formata uma lista de bits em grupos para exibição amigável na interface.
    Exemplo: [0, 1, 0, 0, 0, 0, 0, 1, 1] -> '01000001 1'
    """
    resultado = []
    for i in range(0, len(bits), agrupamento):
        bloco = "".join(str(b) for b in bits[i : i + agrupamento])
        resultado.append(bloco)
    return " ".join(resultado)
