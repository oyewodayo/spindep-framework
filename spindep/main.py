from src.pipeline import run_pipeline


DATASET_ROOT = "./datasets/normalized"

RESULTS_ROOT = "../results"


if __name__ == "__main__":

    run_pipeline(
        dataset_root=DATASET_ROOT,
        results_root=RESULTS_ROOT
    )