import pickle
import numpy as np
from typing import List


def federated_average(weight_files: List[str]) -> List[np.ndarray]:
    """
    Perform Federated Averaging (FedAvg) across multiple model weight files.
    
    Each .pkl file should contain a list of NumPy arrays,
    where each array represents a layer's weights.
    
    FedAvg: For each layer, compute the element-wise average
    of that layer's weights across all participating models.
    
    Args:
        weight_files: List of file paths to .pkl weight files
        
    Returns:
        List of averaged NumPy arrays (one per layer)
        
    Raises:
        ValueError: If weight files are incompatible
    """
    if not weight_files:
        raise ValueError("No weight files provided for aggregation")

    # Load all weights
    all_weights = []
    for fpath in weight_files:
        with open(fpath, "rb") as f:
            data = pickle.load(f)
        
        # Check if the data is a Keras model or a list of weights
        if hasattr(data, "get_weights"):
            # It's a Keras model object
            weights = data.get_weights()
        elif isinstance(data, (list, tuple)):
            # It's already a list of weights
            weights = data
        else:
            raise ValueError(
                f"Weight file {fpath} contains an unsupported type: {type(data).__name__}. "
                f"Expected a list of arrays or a Keras model."
            )
        
        # Convert to numpy arrays if needed
        try:
            weights = [np.array(w, dtype=np.float64) for w in weights]
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"Weight file '{fpath}' contains invalid numerical data. "
                "The file must contain a single Keras model or a list of NumPy weight arrays. "
                "Please do not upload lists of models or objects."
            )
            
        all_weights.append(weights)

    # Validate all have same number of layers
    num_layers = len(all_weights[0])
    for i, (fpath, w) in enumerate(zip(weight_files, all_weights)):
        if len(w) != num_layers:
            raise ValueError(
                f"Weight file '{fpath}' has {len(w)} layers, "
                f"but model 0 has {num_layers} layers. All models must share the same architecture."
            )

    # Validate shapes match across all models for each layer
    for layer_idx in range(num_layers):
        expected_shape = all_weights[0][layer_idx].shape
        for model_idx, (fpath, weights) in enumerate(zip(weight_files, all_weights)):
            actual_shape = weights[layer_idx].shape
            if actual_shape != expected_shape:
                raise ValueError(
                    f"Shape mismatch at layer {layer_idx} in file '{fpath}': "
                    f"expected {expected_shape}, got {actual_shape}."
                )

    # Perform FedAvg: average each layer element-wise
    num_models = len(all_weights)
    avg_weights = []
    
    for layer_idx in range(num_layers):
        layer_sum = np.zeros_like(all_weights[0][layer_idx], dtype=np.float64)
        for model_idx in range(num_models):
            layer_sum += all_weights[model_idx][layer_idx].astype(np.float64)
        layer_avg = (layer_sum / num_models).astype(all_weights[0][layer_idx].dtype)
        avg_weights.append(layer_avg)

    return avg_weights


def save_weights(weights: List[np.ndarray], file_path: str) -> None:
    """Save aggregated weights to a .pkl file."""
    with open(file_path, "wb") as f:
        pickle.dump(weights, f)


def get_model_info(weight_file: str) -> dict:
    """Get information about a weight file."""
    with open(weight_file, "rb") as f:
        data = pickle.load(f)

    if hasattr(data, "get_weights"):
        weights = data.get_weights()
    elif isinstance(data, (list, tuple)):
        weights = data
    else:
        return {"error": "Invalid format", "type": type(data).__name__}

    layers = []
    for i, w in enumerate(weights):
        try:
            arr = np.array(w, dtype=np.float64)
        except (ValueError, TypeError):
            return {"error": f"Invalid layer data at index {i}", "type": type(w).__name__}
        
        layers.append({
            "layer": i,
            "shape": list(arr.shape),
            "dtype": str(arr.dtype),
            "size": int(arr.size),
        })

    return {
        "num_layers": len(weights),
        "layers": layers,
        "total_parameters": sum(l["size"] for l in layers),
    }
