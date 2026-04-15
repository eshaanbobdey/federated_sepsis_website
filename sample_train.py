#!/usr/bin/env python3
"""
Sample Training Script for FedSepsis

This script demonstrates how hospitals can:
1. Train a local sepsis detection model
2. Extract model weights
3. Save weights as a .pkl file for upload to FedSepsis

Usage:
    python sample_train.py

This will generate a sample 'hospital_weights.pkl' file
that can be uploaded to the FedSepsis platform.
"""

import pickle
import numpy as np

# ============================================
# Model Architecture: Feedforward Neural Network
# Input (18 features) → Dense(32) → Dense(16) → Dense(1)
#
# Required input features (ordered):
#   HR, O2Sat, Temp, SBP, MAP, DBP, Resp,
#   Age, Gender, ICULOS,
#   Creatinine, Glucose, Lactate,
#   WBC, Platelets, Hgb, Hct, BUN
# ============================================

# The model has 3 layers with weights + biases:
# Layer 1: Input → 32  (weights: 18x32, bias: 32)
# Layer 2: 32 → 16     (weights: 32x16, bias: 16) 
# Layer 3: 16 → 1      (weights: 16x1,  bias: 1)

FEATURE_NAMES = [
    "HR", "O2Sat", "Temp", "SBP", "MAP", "DBP", "Resp",
    "Age", "Gender", "ICULOS",
    "Creatinine", "Glucose", "Lactate",
    "WBC", "Platelets", "Hgb", "Hct", "BUN",
]


def create_model_weights(seed=None):
    """
    Create model weights for the sepsis detection neural network.
    
    In a real scenario, these weights would come from training
    on your hospital's local dataset using TensorFlow/PyTorch/etc.
    
    For demonstration, we generate random weights with proper shapes.
    
    Returns:
        list of numpy arrays: [W1, b1, W2, b2, W3, b3]
    """
    if seed is not None:
        np.random.seed(seed)
    
    n_features = len(FEATURE_NAMES)  # 18
    
    # Layer 1: Input (18) → Hidden (32)
    W1 = np.random.randn(n_features, 32).astype(np.float32) * 0.1
    b1 = np.zeros(32, dtype=np.float32)
    
    # Layer 2: Hidden (32) → Hidden (16)
    W2 = np.random.randn(32, 16).astype(np.float32) * 0.1
    b2 = np.zeros(16, dtype=np.float32)
    
    # Layer 3: Hidden (16) → Output (1)
    W3 = np.random.randn(16, 1).astype(np.float32) * 0.1
    b3 = np.zeros(1, dtype=np.float32)
    
    weights = [W1, b1, W2, b2, W3, b3]
    return weights


def save_weights(weights, filename="hospital_weights.pkl"):
    """Save model weights to a pickle file."""
    with open(filename, "wb") as f:
        pickle.dump(weights, f)
    print(f"✅ Weights saved to: {filename}")
    return filename


def inspect_weights(filename):
    """Load and inspect a weights file."""
    with open(filename, "rb") as f:
        weights = pickle.load(f)
    
    print(f"\n📦 Weight File: {filename}")
    print(f"   Number of arrays: {len(weights)}")
    print(f"   Layers:")
    
    total_params = 0
    for i, w in enumerate(weights):
        arr = np.array(w)
        total_params += arr.size
        layer_type = "Weight" if i % 2 == 0 else "Bias"
        print(f"     [{i}] {layer_type}: shape={arr.shape}, dtype={arr.dtype}")
    
    print(f"   Total parameters: {total_params:,}")


if __name__ == "__main__":
    print("=" * 50)
    print("FedSepsis — Sample Model Training Script")
    print("=" * 50)
    print(f"\nInput features ({len(FEATURE_NAMES)}):")
    print(f"  {', '.join(FEATURE_NAMES)}")
    print(f"\nModel: Feedforward NN (18 → 32 → 16 → 1)")
    
    # Generate sample weights from 3 different "hospitals"
    for i in range(1, 4):
        print(f"\n--- Hospital {i} ---")
        weights = create_model_weights(seed=42 + i)
        filename = f"hospital_{i}_weights.pkl"
        save_weights(weights, filename)
        inspect_weights(filename)
    
    print(f"\n{'='*50}")
    print("✅ Generated 3 sample weight files.")
    print("Upload these .pkl files to the FedSepsis platform.")
    print("="*50)
