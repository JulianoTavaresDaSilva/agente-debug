def calcular_media(valores):
    if not valores:
        raise ValueError("A lista de valores não pode estar vazia.")
    return sum(valores) / len(valores)
