import argparse
import logging
import os

import yaml
import tempfile
import mlflow
from mlflow.models import infer_signature
from sklearn.impute import SimpleImputer

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import wandb
from sklearn.model_selection import train_test_split
from sklearn.neighbors import LocalOutlierFactor
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import OneHotEncoder
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction import FeatureHasher
from sklearn.metrics import roc_auc_score
from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix
from sklearn.metrics import plot_confusion_matrix
from sklearn.metrics import ConfusionMatrixDisplay
from sklearn.metrics import accuracy_score
from sklearn.feature_extraction import FeatureHasher
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC

# configure logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(message)s",
                    datefmt='%d-%m-%Y %H:%M:%S')

# reference for a logging obj
logger = logging.getLogger()


# Custom Transformer that extracts columns passed as argument to its
# constructor
class FeatureSelector(BaseEstimator, TransformerMixin):
    # Class Constructor
    def __init__(self, feature_names):
        self.feature_names = feature_names

    # Return self nothing else to do here
    def fit(self, X, y=None):
        return self

    # Method that describes what we need this transformer to do
    def transform(self, X, y=None):
        return X[self.feature_names]



class NumericalTransformer(BaseEstimator, TransformerMixin):
    # Class constructor method that takes a model parameter as its argument
    # model 0: minmax
    # model 1: standard
    # model 2: without scaler
    def __init__(self, model=0, colnames=None):
        self.model = model
        self.colnames = colnames

    # Return self nothing else to do here
    def fit(self, X, y=None):
        return self

    # return columns names after transformation
    def get_feature_names(self):
        return self.colnames

    # Transformer method we wrote for this transformer
    def transform(self, X, y=None):
        df = pd.DataFrame(X, columns=self.colnames)

        # update columns name
        self.colnames = df.columns.tolist()

        x_num_mean = df.mean()
        x_num_std = df.std()
        x_num_norm = (df - x_num_mean) / x_num_std

        correlation = np.corrcoef(df, rowvar=False)
        eigvals, eigvect = np.linalg.eig(correlation)
        x_avet = eigvect[:, [0, 3, 5]]
        x_num_dec = np.dot(x_num_norm, x_avet)
        colsPC = ['PC0', 'PC1', 'PC2']
        x_num_dec = pd.DataFrame(x_num_dec, columns=colsPC)
        return x_num_dec


def process_args(args):

    run = wandb.init(job_type="train")

    logger.info("Downloading and reading train artifact")
    local_path = run.use_artifact(args.train_data).file()
    df_train = pd.read_csv(local_path)

    # Spliting train.csv into train and validation dataset
    logger.info("Spliting data into train/val")
    # split-out train/validation and test dataset
    x_train, x_val, y_train, y_val = train_test_split(df_train.drop(labels=args.stratify, axis=1),
                                                      df_train[args.stratify],
                                                      test_size=args.val_size,
                                                      random_state=args.random_seed,
                                                      shuffle=True,
                                                      stratify=df_train[args.stratify])

    logger.info("x train: {}".format(x_train.shape))
    logger.info("y train: {}".format(y_train.shape))
    logger.info("x val: {}".format(x_val.shape))
    logger.info("y val: {}".format(y_val.shape))

    logger.info("Removal Outliers")
    # temporary variable
    x = x_train.select_dtypes("int64").copy()

    # identify outlier in the dataset
    lof = LocalOutlierFactor()
    outlier = lof.fit_predict(x)
    mask = outlier != -1

    logger.info("x_train shape [original]: {}".format(x_train.shape))
    logger.info("x_train shape [outlier removal]: {}".format(
        x_train.loc[mask, :].shape))

    # dataset without outlier, note this step could be done during the
    # preprocesing stage
    x_train = x_train.loc[mask, :].copy()
    y_train = y_train[mask].copy()

    logger.info("Encoding Target Variable")
    # define a categorical encoding for target variable
    le = LabelEncoder()

    # fit and transform y_train
    y_train = le.fit_transform(y_train)

    # transform y_test (avoiding data leakage)
    y_val = le.transform(y_val)

    logger.info("Classes [0, 1]: {}".format(le.inverse_transform([0, 1])))

    # Pipeline generation
    logger.info("Pipeline generation")

    # Get the configuration for the pipeline
    with open(args.model_config) as fp:
        model_config = yaml.safe_load(fp)

    # Add it to the W&B configuration so the values for the hyperparams
    # are tracked
    wandb.config.update(model_config)

    # Categrical features to pass down the categorical pipeline
    categorical_features = ['Cidade', 'Ocupacao', 'AreaAtuacao']

    # Numerical features to pass down the numerical pipeline
    numerical_features = [
        'Idade',
        'EstadoCivil',
        'Escolaridade',
        'NivelGerencial',
        'TipoResidencia',
        'CondicaoResidencia',
        'ValorImovel',
        'NoAutomoveis']

    # Defining the steps in the categorical pipeline
    categorical_pipeline = Pipeline(steps=[('cat_selector', FeatureSelector(categorical_features)),
                                           ('cat_encoder',OneHotEncoder(handle_unknown = 'ignore'))
                                           ]
                                    )
    # Defining the steps in the numerical pipeline
    numerical_pipeline = Pipeline(steps=[('num_selector', FeatureSelector(numerical_features)),
                                         ('num_transformer', NumericalTransformer(model_config["numerical_pipe"]["model"],
                                                                                  colnames=numerical_features))
                                         ]
                                  )

    # Combining numerical and categorical piepline into one full big pipeline horizontally
    # using FeatureUnion
    full_pipeline_preprocessing = FeatureUnion(transformer_list=[('cat_pipeline', categorical_pipeline),
                                                                 ('num_pipeline',
                                                                  numerical_pipeline)
                                                                 ]
                                               )

    # The full pipeline
    pipe = Pipeline(steps=[('full_pipeline', full_pipeline_preprocessing),
                           ("classifier", SVC(**model_config["svm"]))
                           ]
                    )

    # training
    logger.info("Training")
    pipe.fit(x_train, y_train)

    # predict
    logger.info("Infering")
    predict = pipe.predict(x_val)

    # Evaluation Metrics
    logger.info("Evaluation metrics")
    # Metric: AUC
    auc = roc_auc_score(y_val, predict, average="macro")
    run.summary["AUC"] = auc

    # Metric: Accuracy
    acc = accuracy_score(y_val, predict)
    run.summary["Accuracy"] = acc

    # Metric: Confusion Matrix
    fig_confusion_matrix, ax = plt.subplots(1, 1, figsize=(7, 4))
    ConfusionMatrixDisplay(confusion_matrix(predict,
                                            y_val,
                                            labels=[1, 0]),
                           display_labels=["Prejuizo", "Lucro"]
                           ).plot(values_format=".0f", ax=ax)
    ax.set_xlabel("True Label")
    ax.set_ylabel("Predicted Label")

    # Metric: renderize the tree
    # full pipeline
    features_full = pipe.named_steps['full_pipeline']


    logger.info("Uploading figures")
    run.log(
        {
            "confusion_matrix": wandb.Image(fig_confusion_matrix)
        }
    )

    # Export if required
    if args.export_artifact != "null":
        export_model(run, pipe, x_val, predict, args.export_artifact)


def export_model(run, pipe, x_val, val_pred, export_artifact):

    # Infer the signature of the model
    signature = infer_signature(x_val, val_pred)

    with tempfile.TemporaryDirectory() as temp_dir:

        export_path = os.path.join(temp_dir, "model_export")

        mlflow.sklearn.save_model(
            pipe,  # our pipeline
            export_path,  # Path to a directory for the produced package
            serialization_format=mlflow.sklearn.SERIALIZATION_FORMAT_CLOUDPICKLE,
            signature=signature,  # input and output schema
            input_example=x_val.iloc[:2],  # the first few examples
        )

        artifact = wandb.Artifact(
            export_artifact,
            type="model_export",
            description="SVC pipeline export",
        )

        # NOTE that we use .add_dir and not .add_file
        # because the export directory contains several
        # files
        artifact.add_dir(export_path)

        run.log_artifact(artifact)

        # Make sure the artifact is uploaded before the temp dir
        # gets deleted
        artifact.wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train a SVM",
        fromfile_prefix_chars="@",
    )

    parser.add_argument(
        "--train_data",
        type=str,
        help="Fully-qualified name for the training data artifact",
        required=True,
    )

    parser.add_argument(
        "--model_config",
        type=str,
        help="Path to a YML file containing the configuration for the random forest",
        required=True,
    )

    parser.add_argument(
        "--export_artifact",
        type=str,
        help="Name of the artifact for the exported model. Use 'null' for no export.",
        required=False,
        default="null",
    )

    parser.add_argument(
        "--random_seed",
        type=int,
        help="Seed for the random number generator.",
        required=False,
        default=42
    )

    parser.add_argument(
        "--val_size",
        type=float,
        help="Size for the validation set as a fraction of the training set",
        required=False,
        default=0.3
    )

    parser.add_argument(
        "--stratify",
        type=str,
        help="Name of a column to be used for stratified sampling. Default: 'null', i.e., no stratification",
        required=False,
        default="null",
    )

    ARGS = parser.parse_args()

    process_args(ARGS)
