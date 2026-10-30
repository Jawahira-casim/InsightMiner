# =========================================================
# InsightMiner - Machine Learning Prediction Module
# routes/prediction.py
# =========================================================

from io import BytesIO
import base64

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from flask import (
    Blueprint,
    render_template,
    request,
    session
)

from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    roc_curve
)

from sklearn.model_selection import (
    train_test_split,
    cross_val_score,
    StratifiedKFold
)

from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier

from sklearn.pipeline import Pipeline

from sklearn.preprocessing import (
    LabelEncoder,
    StandardScaler
)

import shared

from activity import log_activity
from decorators import role_required


# =========================================================
# Blueprint
# =========================================================

prediction_bp = Blueprint(
    "prediction",
    __name__
)


# =========================================================
# Convert Matplotlib Figure to Base64
# =========================================================

def figure_to_base64():

    buffer = BytesIO()

    plt.tight_layout()

    plt.savefig(
        buffer,
        format="png",
        dpi=120,
        bbox_inches="tight"
    )

    plt.close()

    buffer.seek(0)

    image_base64 = base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")

    buffer.close()

    return image_base64


# =========================================================
# Actual vs Predicted Graph
# =========================================================

def create_actual_vs_predicted_image(
    actual,
    predicted
):

    plt.figure(
        figsize=(8, 5)
    )

    plt.scatter(
        actual,
        predicted,
        alpha=0.7
    )

    minimum_value = min(
        float(min(actual)),
        float(min(predicted))
    )

    maximum_value = max(
        float(max(actual)),
        float(max(predicted))
    )

    plt.plot(
        [
            minimum_value,
            maximum_value
        ],
        [
            minimum_value,
            maximum_value
        ],
        linestyle="--"
    )

    plt.xlabel(
        "Actual Values"
    )

    plt.ylabel(
        "Predicted Values"
    )

    plt.title(
        "Actual vs Predicted Values"
    )

    plt.grid(
        alpha=0.25
    )

    return figure_to_base64()


# =========================================================
# Residual Plot
# =========================================================

def create_residual_plot_image(
    actual,
    predicted
):

    residuals = (
        actual - predicted
    )

    plt.figure(
        figsize=(8, 5)
    )

    plt.scatter(
        predicted,
        residuals,
        alpha=0.7
    )

    plt.axhline(
        y=0,
        linestyle="--"
    )

    plt.xlabel(
        "Predicted Values"
    )

    plt.ylabel(
        "Residuals"
    )

    plt.title(
        "Residual Plot"
    )

    plt.grid(
        alpha=0.25
    )

    return figure_to_base64()


# =========================================================
# Confusion Matrix Image
# =========================================================

def create_confusion_matrix_image(
    matrix,
    class_names
):

    plt.figure(
        figsize=(7, 5)
    )

    image = plt.imshow(
        matrix,
        interpolation="nearest",
        cmap="Blues"
    )

    plt.colorbar(
        image
    )

    plt.title(
        "Confusion Matrix Heatmap"
    )

    plt.xlabel(
        "Predicted Class"
    )

    plt.ylabel(
        "Actual Class"
    )

    positions = range(
        len(class_names)
    )

    plt.xticks(
        positions,
        class_names
    )

    plt.yticks(
        positions,
        class_names
    )

    threshold = (
        matrix.max() / 2
        if matrix.size
        else 0
    )

    for row_index in range(
        matrix.shape[0]
    ):

        for column_index in range(
            matrix.shape[1]
        ):

            value = matrix[
                row_index,
                column_index
            ]

            text_colour = (
                "white"
                if value > threshold
                else "black"
            )

            plt.text(
                column_index,
                row_index,
                str(value),
                horizontalalignment="center",
                verticalalignment="center",
                color=text_colour,
                fontsize=12,
                fontweight="bold"
            )

    return figure_to_base64()


# =========================================================
# ROC Curve
# =========================================================

def create_roc_image(
    actual,
    probabilities
):

    false_positive_rate, true_positive_rate, _ = (
        roc_curve(
            actual,
            probabilities
        )
    )

    auc_score = roc_auc_score(
        actual,
        probabilities
    )

    plt.figure(
        figsize=(8, 5)
    )

    plt.plot(
        false_positive_rate,
        true_positive_rate,
        label=(
            f"ROC Curve "
            f"(AUC = {auc_score:.3f})"
        )
    )

    plt.plot(
        [0, 1],
        [0, 1],
        linestyle="--",
        label="Random Classifier"
    )

    plt.xlabel(
        "False Positive Rate"
    )

    plt.ylabel(
        "True Positive Rate"
    )

    plt.title(
        "Receiver Operating Characteristic Curve"
    )

    plt.legend(
        loc="lower right"
    )

    plt.grid(
        alpha=0.25
    )

    image = figure_to_base64()

    return (
        image,
        float(auc_score)
    )


# =========================================================
# Linear Regression
# =========================================================

def run_linear_regression(
    df,
    target
):

    # -----------------------------------------------------
    # Validate target
    # -----------------------------------------------------

    if target not in df.columns:

        raise ValueError(
            "The selected target column "
            "does not exist."
        )

    if not pd.api.types.is_numeric_dtype(
        df[target]
    ):

        raise ValueError(
            "Linear Regression requires "
            "a numeric target column."
        )

    # -----------------------------------------------------
    # Numeric data only
    # -----------------------------------------------------

    numeric_df = df.select_dtypes(
        include="number"
    ).copy()

    numeric_df = numeric_df.dropna(
        subset=[target]
    )

    if len(numeric_df) < 10:

        raise ValueError(
            "At least 10 valid records "
            "are required for prediction."
        )

    # -----------------------------------------------------
    # Feature columns
    # -----------------------------------------------------

    feature_columns = [
        column
        for column in numeric_df.columns
        if column != target
    ]

    # -----------------------------------------------------
    # Prevent regression target leakage
    # -----------------------------------------------------

    if (
        target.strip().lower()
        == "final_exam_score"
    ):

        leakage_columns = {
            "final_marks"
        }

        feature_columns = [
            column
            for column in feature_columns
            if column.strip().lower()
            not in leakage_columns
        ]

    if not feature_columns:

        raise ValueError(
            "At least one numeric feature "
            "column is required."
        )

    # -----------------------------------------------------
    # X and y
    # -----------------------------------------------------

    X = numeric_df[
        feature_columns
    ]

    y = numeric_df[
        target
    ]

    # -----------------------------------------------------
    # Split
    # -----------------------------------------------------

    (
        X_train,
        X_test,
        y_train,
        y_test
    ) = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42
    )

    # -----------------------------------------------------
    # Pipeline
    # -----------------------------------------------------

    model = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                )
            ),
            (
                "regressor",
                LinearRegression()
            )
        ]
    )

    # -----------------------------------------------------
    # Train
    # -----------------------------------------------------

    model.fit(
        X_train,
        y_train
    )

    # -----------------------------------------------------
    # Cross validation
    # -----------------------------------------------------

    cv_scores = cross_val_score(
        model,
        X,
        y,
        cv=5,
        scoring="r2"
    )

    cv_mean = float(
        cv_scores.mean()
    )

    # -----------------------------------------------------
    # Predictions
    # -----------------------------------------------------

    predictions = model.predict(
        X_test
    )

    # -----------------------------------------------------
    # Metrics
    # -----------------------------------------------------

    r2 = float(
        r2_score(
            y_test,
            predictions
        )
    )

    mae = float(
        mean_absolute_error(
            y_test,
            predictions
        )
    )

    rmse = float(
        mean_squared_error(
            y_test,
            predictions
        ) ** 0.5
    )

    # -----------------------------------------------------
    # Charts
    # -----------------------------------------------------

    actual_vs_predicted_image = (
        create_actual_vs_predicted_image(
            y_test,
            predictions
        )
    )

    residual_plot_image = (
        create_residual_plot_image(
            y_test,
            predictions
        )
    )

    # -----------------------------------------------------
    # Interpretation
    # -----------------------------------------------------

    if r2 >= 0.80:

        performance = "excellent"

    elif r2 >= 0.50:

        performance = "good"

    elif r2 >= 0.30:

        performance = "moderate"

    elif r2 >= 0:

        performance = "low"

    else:

        performance = "poor"

    interpretation = (
        f"The Linear Regression model achieved "
        f"an R² score of {r2:.3f}, indicating "
        f"{performance} predictive performance. "
        f"The Mean Absolute Error (MAE) was "
        f"{mae:.3f} and the Root Mean Squared "
        f"Error (RMSE) was {rmse:.3f}. "
        f"The 5-fold cross-validation R² score "
        f"was {cv_mean:.3f}, which provides an "
        f"additional estimate of how well the "
        f"model may generalise to unseen data."
    )

    # -----------------------------------------------------
    # Result
    # -----------------------------------------------------

    result = {

        "task_type":
            "regression",

        "algorithm_name":
            "Linear Regression",

        "target":
            target,

        "features":
            feature_columns,

        "training_records":
            len(X_train),

        "testing_records":
            len(X_test),

        "r2":
            r2,

        "mae":
            mae,

        "rmse":
            rmse,

        "cv_score":
            cv_mean,

        "actual_vs_predicted_image":
            actual_vs_predicted_image,

        "residual_plot_image":
            residual_plot_image,

        "interpretation":
            interpretation
    }

    shared.latest_prediction_result = (
        result
    )

    return result


# =========================================================
# Classification
# =========================================================

def run_classification(
    df,
    target,
    algorithm
):

    # -----------------------------------------------------
    # Validate target
    # -----------------------------------------------------

    if target not in df.columns:

        raise ValueError(
            "The selected target column "
            "does not exist."
        )

    # -----------------------------------------------------
    # Numeric feature columns
    # -----------------------------------------------------

    feature_columns = [
        column
        for column in df.select_dtypes(
            include="number"
        ).columns
        if column != target
    ]

    # -----------------------------------------------------
    # Prevent target leakage
    # -----------------------------------------------------

    if (
        target.strip().lower()
        == "result"
    ):

        leakage_columns = {
            "final_marks",
            "final_exam_score",
            "previous_result"
        }

        feature_columns = [
            column
            for column in feature_columns
            if column.strip().lower()
            not in leakage_columns
        ]

    if not feature_columns:

        raise ValueError(
            "Classification requires at least "
            "one numeric feature column."
        )

    # -----------------------------------------------------
    # Working dataframe
    # -----------------------------------------------------

    working_df = df[
        feature_columns + [target]
    ].copy()

    working_df = working_df.dropna(
        subset=[target]
    )

    if len(working_df) < 10:

        raise ValueError(
            "At least 10 valid records are "
            "required for classification."
        )

    # -----------------------------------------------------
    # Features
    # -----------------------------------------------------

    X = working_df[
        feature_columns
    ]

    # -----------------------------------------------------
    # Target
    # -----------------------------------------------------

    original_target = (
        working_df[target]
        .astype(str)
        .str.strip()
    )

    if original_target.nunique() < 2:

        raise ValueError(
            "The target column must contain "
            "at least two different classes."
        )

    # -----------------------------------------------------
    # Encode target
    # -----------------------------------------------------

    label_encoder = (
        LabelEncoder()
    )

    y = label_encoder.fit_transform(
        original_target
    )

    class_names = (
        label_encoder
        .classes_
        .tolist()
    )

    number_of_classes = len(
        class_names
    )

    # -----------------------------------------------------
    # Validate class counts
    # -----------------------------------------------------

    class_counts = (
        pd.Series(y)
        .value_counts()
    )

    minimum_class_count = int(
        class_counts.min()
    )

    if minimum_class_count < 2:

        raise ValueError(
            "Every target class must contain "
            "at least two records."
        )

    # -----------------------------------------------------
    # Train/Test split
    # -----------------------------------------------------

    try:

        (
            X_train,
            X_test,
            y_train,
            y_test
        ) = train_test_split(
            X,
            y,
            test_size=0.20,
            random_state=42,
            stratify=y
        )

    except ValueError as error:

        raise ValueError(
            "The dataset does not contain "
            "enough records in each class "
            "for a reliable train/test split."
        ) from error

    # -----------------------------------------------------
    # Gaussian Naive Bayes
    # -----------------------------------------------------

    if algorithm == "naive_bayes":

        model = Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="median"
                    )
                ),
                (
                    "classifier",
                    GaussianNB()
                )
            ]
        )

        algorithm_name = (
            "Gaussian Naïve Bayes"
        )

    # -----------------------------------------------------
    # KNN
    # -----------------------------------------------------

    elif algorithm == "knn":

        number_of_neighbors = min(
            5,
            len(X_train)
        )

        model = Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(
                        strategy="median"
                    )
                ),
                (
                    "scaler",
                    StandardScaler()
                ),
                (
                    "classifier",
                    KNeighborsClassifier(
                        n_neighbors=
                        number_of_neighbors
                    )
                )
            ]
        )

        algorithm_name = (
            "K-Nearest Neighbors "
            f"(K = {number_of_neighbors})"
        )

    else:

        raise ValueError(
            "Invalid classification algorithm."
        )

    # -----------------------------------------------------
    # Train
    # -----------------------------------------------------

    model.fit(
        X_train,
        y_train
    )

    # -----------------------------------------------------
    # Cross validation
    # -----------------------------------------------------

    number_of_folds = min(
        5,
        minimum_class_count
    )

    cv_strategy = StratifiedKFold(
        n_splits=number_of_folds,
        shuffle=True,
        random_state=42
    )

    cv_scores = cross_val_score(
        model,
        X,
        y,
        cv=cv_strategy,
        scoring="accuracy"
    )

    cv_mean = float(
        cv_scores.mean()
    )

    # -----------------------------------------------------
    # Prediction
    # -----------------------------------------------------

    predictions = model.predict(
        X_test
    )

    probabilities = model.predict_proba(
        X_test
    )

    # -----------------------------------------------------
    # Metrics
    # -----------------------------------------------------

    accuracy = float(
        accuracy_score(
            y_test,
            predictions
        )
    )

    average_method = (
        "binary"
        if number_of_classes == 2
        else "weighted"
    )

    precision = float(
        precision_score(
            y_test,
            predictions,
            average=average_method,
            zero_division=0
        )
    )

    recall = float(
        recall_score(
            y_test,
            predictions,
            average=average_method,
            zero_division=0
        )
    )

    f1 = float(
        f1_score(
            y_test,
            predictions,
            average=average_method,
            zero_division=0
        )
    )

    # -----------------------------------------------------
    # Classification Report
    # -----------------------------------------------------

    report = classification_report(
        y_test,
        predictions,
        labels=list(
            range(number_of_classes)
        ),
        target_names=class_names,
        output_dict=True,
        zero_division=0
    )

    # -----------------------------------------------------
    # Confusion Matrix
    # -----------------------------------------------------

    matrix = confusion_matrix(
        y_test,
        predictions,
        labels=list(
            range(number_of_classes)
        )
    )

    confusion_matrix_image = (
        create_confusion_matrix_image(
            matrix,
            class_names
        )
    )

    confusion_matrix_rows = []

    for index, row in enumerate(
        matrix.tolist()
    ):

        confusion_matrix_rows.append(
            {
                "actual_class":
                    class_names[index],

                "values":
                    row
            }
        )

    # -----------------------------------------------------
    # ROC / AUC
    # -----------------------------------------------------

    roc_image = None
    auc_score = None
    roc_message = None

    if number_of_classes == 2:

        try:

            positive_probabilities = (
                probabilities[:, 1]
            )

            (
                roc_image,
                auc_score
            ) = create_roc_image(
                y_test,
                positive_probabilities
            )

        except ValueError:

            roc_message = (
                "ROC Curve could not be generated "
                "because the test set does not "
                "contain both classes."
            )

    else:

        roc_message = (
            "ROC Curve is displayed only for "
            "binary classification. "
            f"The selected target contains "
            f"{number_of_classes} classes."
        )

    # -----------------------------------------------------
    # Prediction counts
    # -----------------------------------------------------

    correct_predictions = int(
        matrix.trace()
    )

    total_predictions = int(
        matrix.sum()
    )

    incorrect_predictions = (
        total_predictions
        - correct_predictions
    )

    # -----------------------------------------------------
    # Interpretation
    # -----------------------------------------------------

    if accuracy >= 0.99:

        interpretation = (
            f"The {algorithm_name} model achieved "
            f"{accuracy * 100:.2f}% test accuracy. "
            f"The model correctly classified "
            f"{correct_predictions} out of "
            f"{total_predictions} test records, "
            f"with {incorrect_predictions} "
            f"incorrect prediction(s). "
            f"The {number_of_folds}-fold "
            f"cross-validation accuracy was "
            f"{cv_mean * 100:.2f}%. "
            f"The high performance indicates that "
            f"the selected academic features strongly "
            f"separate the target classes in this "
            f"dataset. Columns that could directly "
            f"reveal the Result were excluded from "
            f"the feature set. Performance should "
            f"nevertheless be interpreted in the "
            f"context of this dataset and should "
            f"not automatically be assumed to "
            f"represent all future real-world "
            f"student data."
        )

    else:

        if accuracy >= 0.90:
            performance = "excellent"

        elif accuracy >= 0.80:
            performance = "very good"

        elif accuracy >= 0.70:
            performance = "good"

        elif accuracy >= 0.60:
            performance = "moderate"

        else:
            performance = "low"

        interpretation = (
            f"The {algorithm_name} model achieved "
            f"{accuracy * 100:.2f}% test accuracy, "
            f"indicating {performance} "
            f"classification performance. "
            f"The model correctly classified "
            f"{correct_predictions} out of "
            f"{total_predictions} test records, "
            f"with {incorrect_predictions} "
            f"incorrect prediction(s). "
            f"The {number_of_folds}-fold "
            f"cross-validation accuracy was "
            f"{cv_mean * 100:.2f}%."
        )

    # -----------------------------------------------------
    # Result dictionary
    # -----------------------------------------------------

    result = {

        "task_type":
            "classification",

        "algorithm_name":
            algorithm_name,

        "target":
            target,

        "features":
            feature_columns,

        "training_records":
            len(X_train),

        "testing_records":
            len(X_test),

        "class_names":
            class_names,

        "accuracy":
            accuracy,

        "precision":
            precision,

        "recall":
            recall,

        "f1":
            f1,

        "cv_score":
            cv_mean,

        "classification_report":
            report,

        "confusion_matrix_rows":
            confusion_matrix_rows,

        "confusion_matrix_image":
            confusion_matrix_image,

        "roc_image":
            roc_image,

        "auc_score":
            auc_score,

        "roc_message":
            roc_message,

        "interpretation":
            interpretation
    }

    shared.latest_prediction_result = (
        result
    )

    return result


# =========================================================
# Prediction Page Route
# =========================================================

@prediction_bp.route(
    "/prediction",
    methods=["GET", "POST"]
)
@role_required(
    "Admin",
    "Analyst",
    "Viewer"
)
def prediction():

    result = None
    error = None

    if shared.current_df is None:

        return render_template(
            "prediction.html",
            columns=[],
            numeric_columns=[],
            categorical_columns=[],
            result=None,
            error=(
                "Please upload a dataset "
                "before running prediction."
            )
        )

    df = shared.current_df.copy()

    # All columns
    columns = df.columns.tolist()

    # Numeric columns
    numeric_columns = (
        df.select_dtypes(
            include="number"
        )
        .columns
        .tolist()
    )

    # Categorical columns
    categorical_columns = (
        df.select_dtypes(
            exclude="number"
        )
        .columns
        .tolist()
    )

    if request.method == "POST":

        algorithm = (
            request.form.get(
                "algorithm",
                ""
            )
            .strip()
        )

        target = (
            request.form.get(
                "target",
                ""
            )
            .strip()
        )

        try:

            if not algorithm:
                raise ValueError(
                    "Please select a "
                    "prediction algorithm."
                )

            if not target:
                raise ValueError(
                    "Please select a "
                    "target column."
                )

            # Linear Regression
            if algorithm == "linear_regression":

                result = run_linear_regression(
                    df,
                    target
                )

            # Classification
            elif algorithm in [
                "naive_bayes",
                "knn"
            ]:

                result = run_classification(
                    df,
                    target,
                    algorithm
                )

            else:

                raise ValueError(
                    "Invalid prediction "
                    "algorithm selected."
                )

            username = session.get(
                "username"
            )

            if username:

                log_activity(
                    username,
                    (
                        "Ran prediction using "
                        f"{result['algorithm_name']} "
                        f"with target {target}"
                    )
                )

        except Exception as exception:

            error = (
                "Prediction could not be completed: "
                f"{str(exception)}"
            )

    return render_template(
        "prediction.html",
        columns=columns,
        numeric_columns=numeric_columns,
        categorical_columns=categorical_columns,
        result=result,
        error=error
    )