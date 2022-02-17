import pandas as pd
import scipy.stats

# Non Deterministic Test
def test_kolmogorov_smirnov(data, ks_alpha):

    sample1, sample2 = data

    numerical_columns = [
        "Idade",
        "NumeroFilhos",
        "Escolaridade",
        "NivelGerencial",
        "TipoResidencia",
        "CondicaoResidencia",
        "ValorImovel",
        "NoAutomoveis"
    ]
    
    # Bonferroni correction for multiple hypothesis testing
    alpha_prime = 1 - (1 - ks_alpha)**(1 / len(numerical_columns))

    for col in numerical_columns:

        # two-sided: The null hypothesis is that the two distributions are identical
        # the alternative is that they are not identical.
        ts, p_value = scipy.stats.ks_2samp(
            sample1[col],
            sample2[col],
            alternative='two-sided'
        )

        # NOTE: as always, the p-value should be interpreted as the probability of
        # obtaining a test statistic (TS) equal or more extreme that the one we got
        # by chance, when the null hypothesis is true. If this probability is not
        # large enough, this dataset should be looked at carefully, hence we fail
        assert p_value > alpha_prime
        
# Determinstic Test
def test_column_presence_and_type(data):
    
    # Disregard the reference dataset
    _, df = data

    required_columns = {
        "Cidade": pd.api.types.is_int64_dtype,
        "Idade": pd.api.types.is_int64_dtype,
        "Sexo": pd.api.types.is_int64_dtype,
        "EstadoCivil": pd.api.types.is_int64_dtype,
        "NumeroFilhos": pd.api.types.is_int64_dtype,
        "Escolaridade": pd.api.types.is_int64_dtype,
        "Ocupacao": pd.api.types.is_int64_dtype,
        "AreaAtuacao": pd.api.types.is_int64_dtype,
        "NivelGerencial": pd.api.types.is_int64_dtype,
        "TipoResidencia": pd.api.types.is_int64_dtype,
        "CondicaoResidencia": pd.api.types.is_int64_dtype,
        "ValorImovel": pd.api.types.is_int64_dtype,  
        "NoAutomoveis": pd.api.types.is_int64_dtype,
        "Computador": pd.api.types.is_int64_dtype,
        "PrimeiraCompra": pd.api.types.is_float_dtype
    }

    # Check column presence
    assert set(df.columns.values).issuperset(set(required_columns.keys()))

    for col_name, format_verification_funct in required_columns.items():

        assert format_verification_funct(df[col_name]), f"Column {col_name} failed test {format_verification_funct}"

# Deterministic Test
def test_class_names(data):
    
    # Disregard the reference dataset
    _, df = data

    # Check that only the known classes are present
    known_classes = [
        1.0,
        0.0
    ]

    assert df["PrimeiraCompra"].isin(known_classes).all()

# Deterministic Test
def test_column_ranges(data):
    
    # Disregard the reference dataset
    _, df = data

    ranges = {
        "Cidade":(1,10),
        "Idade": (18,64),
        "Sexo": (1,2),
        "EstadoCivil": (1,4),
        "NumeroFilhos": (0,4),
        "Escolaridade": (0,4),
        "Ocupacao": (0,7),
        "AreaAtuacao": (0,9),
        "NivelGerencial": (1,7),
        "TipoResidencia": (1,3),
        "CondicaoResidencia": (1,4),
        "ValorImovel": (1,5),  
        "NoAutomoveis": (0,3),
        "Computador": (1,2),
        "PrimeiraCompra": (0.0,1.0)
    }

    for col_name, (minimum, maximum) in ranges.items():

        assert df[col_name].dropna().between(minimum, maximum).all(), (
            f"Column {col_name} failed the test. Should be between {minimum} and {maximum}, "
            f"instead min={df[col_name].min()} and max={df[col_name].max()}"
        )
