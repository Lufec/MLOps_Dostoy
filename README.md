# MLOps: Caso Dostoy

Esse repositório contém os códigos necessários para construir um modelo de classificação usando SVM, sua análise e seu deploy.

Ferramentas necessárias:

![image](https://user-images.githubusercontent.com/30414428/154772095-11469e69-c83c-4061-ba47-7cd2dec1c84e.png)
Fonte: Ivanovitch Silva


Estrutura:

![image](https://user-images.githubusercontent.com/30414428/154772118-af191353-a76c-4188-af2a-26c10982b490.png)
Fonte: Ivanovitch Silva

O código consiste no uso de módulos, sendo eles:

* Download
* Pré-processamento
* Checagem de dados
* Separação de conjuntos
* Treinamento
* Avaliação

Para executar todos os módulos em uma única chamada, é necessário, primeiramente, configurar o login do WandB. Em seguida, é possível realizar a chamada do seguinte comando:

```
mlflow run -v 1.0.0 https://github.com/Lufec/MLOps_Dostoy.git -P hydra_options="main.project_name=MLOps_Dostoy"
```
O argumento "project_name" pode ser qualquer nome que achar relevante e/ou desejar.

Caso desejado, é possível executar apenas certos módulos por comando, por exemplo:

```
mlflow run . -P hydra_options="main.execute_steps='download_data'"
```

Sobre a problemática, ela consiste em um exercício de classificação rpesente no seguinte repositório : https://github.com/Lufec/Caso_Dostoy

O objetivo é, a partir do perfil das pessoas que a empresa Dostoy coletou, identificar para quais ela deve enviar catálogos de produto tal que ela possua Lucro (classe 1) ou evitar envio de catálogos em caso de Prejuízo (classe 0), uma vez que o envio de catálogos possui um preço fixo.

O conjunto de teste, utilizando todo o pipeline elaborado no código do repositório, retornou uma acurácia de 84%.

![image](https://user-images.githubusercontent.com/30414428/154773001-f5dc6132-6b85-4166-8532-c7f4be8cf549.png)


Por fim, para realizar o deploy e fazer inferências online, é necessario chamar os seguintes comando:

1) Para recuperar o modelo e seus hiperparâmetros calculados;

```
wandb artifact get Dostoy_Case/model_export:latest --root model
```

2) Para criar uma REST API para realizar requests ao endpoint gerado;

```
mlflow models serve -m model
```

Executar um script que realize esse request, por exemplo o contido no notebook "Online Reference"


Essa estrutura possuiu como base o repositório gerado por Ivanovitch Silva, disponível em:

https://github.com/ivanovitchm/mlops
