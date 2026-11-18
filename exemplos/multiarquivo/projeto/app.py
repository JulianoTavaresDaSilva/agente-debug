from dominio.descontos import total_com_desconto


def finalizar_pedido():
    return total_com_desconto(100, 10)


if __name__ == "__main__":
    print(finalizar_pedido())
