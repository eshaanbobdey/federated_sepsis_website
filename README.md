# Federated Sepsis Prediction Platform

A privacy-preserving federated learning platform for **early sepsis prediction** across multiple hospitals. Sepsis is a life-threatening condition caused by the body's response to infection, and early detection is critical for patient survival. This system enables hospitals to collaboratively train a global AI model without sharing raw patient data, using the FedAvg (Federated Averaging) algorithm.

The platform uses an **Artificial Neural Network (ANN)** trained on clinical features such as heart rate, oxygen saturation, temperature, blood pressure, age, and lab results to predict sepsis risk in ICU patients.

## Features

- **Federated Learning**: Train a global model using locally-stored hospital data
- **Privacy-Preserving**: Raw patient data never leaves hospital premises
- **Weight Aggregation**: Secure aggregation of model weights using FedAvg algorithm
- **Multi-Hospital Support**: Support for multiple participating hospitals
- **Admin Dashboard**: Monitor training progress and model performance
- **Google OAuth**: Secure authentication for hospital administrators
- **RESTful API**: Easy integration with existing hospital systems

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Hospital 1    │     │   Hospital 2    │     │   Hospital 3    │
│  (Local Data)   │     │  (Local Data)   │     │  (Local Data)   │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────┬───────────┴───────────┬───────────┘
                     │                       │
              ┌──────▼──────┐       ┌───────▼──────┐
              │   Upload    │       │   Upload     │
              │   Weights   │       │   Weights    │
              └──────┬──────┘       └───────┬──────┘
                     │                       │
                     └───────────┬───────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Federated Server      │
                    │   (Weight Aggregation)  │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    Global Model         │
                    │    (Aggregated)         │
                    └─────────────────────────┘
```

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTML5, CSS3, JavaScript
- **Database**: PostgreSQL (with asyncpg)
- **Authentication**: Google OAuth 2.0 + JWT
- **ML Framework**: TensorFlow/Keras
- **Federated Algorithm**: FedAvg

## Installation

1. Clone the repository:
```bash
git clone https://github.com/eshaanbobdey/federated_sepsis_website.git
cd federated_sepsis_website
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Set up PostgreSQL database and update `DATABASE_URL` in `.env`

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `ADMIN_EMAIL` | Admin email for access control |
| `JWT_SECRET` | Secret key for JWT token generation |

## Usage

1. Start the backend server:
```bash
uvicorn backend.main:app --reload
```

2. Open `frontend/index.html` in your browser

3. Sign in with Google credentials

4. Access the dashboard to manage federated training rounds

## Project Structure

```
federated-learning-website/
├── backend/
│   ├── models/          # Database models (User, Weight, GlobalModel)
│   ├── routes/          # API endpoints (auth, weights, aggregate)
│   ├── services/        # FedAvg aggregation logic
│   ├── config.py        # Configuration settings
│   ├── database.py      # Database connection
│   └── main.py          # FastAPI application entry
├── frontend/
│   ├── index.html       # Landing page
│   ├── dashboard.html   # Hospital dashboard
│   ├── admin.html       # Admin panel
│   ├── styles.css       # Styling
│   └── script.js        # Frontend logic
├── global_models/       # Stored global model weights
├── weights/             # Individual hospital weights
├── requirements.txt     # Python dependencies
└── .env.example         # Environment template
```

## Model Training

To train your own local model for federated learning, see [`sample_train.py`](sample_train.py). This script demonstrates how to:

1. Load and preprocess the sepsis dataset
2. Train an Artificial Neural Network (ANN) with the architecture: **18 → 32 → 16 → 1**
3. Handle class imbalance using balanced class weights
4. Extract and save model weights as a `.pkl` file

**Input Features (18):**
`HR`, `O2Sat`, `Temp`, `SBP`, `MAP`, `DBP`, `Resp`, `Age`, `Gender`, `ICULOS`, `Creatinine`, `Glucose`, `Lactate`, `WBC`, `Platelets`, `Hgb`, `Hct`, `BUN`

**Quick Start:**
```bash
python sample_train.py
```

This will generate `hospital_weights.pkl` files ready for upload to the platform.

> **Note**: Save your trained model as a `.pkl` file and upload it through the dashboard to participate in federated learning rounds.

## How It Works

1. **Local Training**: Each hospital trains a local model on their private data
2. **Weight Upload**: Hospitals upload only model weights (not data) to the central server
3. **Aggregation**: Server aggregates weights using FedAvg algorithm: 
   $$W_{global} = \sum_{i=1}^{n} \frac{n_i}{N} W_i$$
   where $n_i$ is the number of samples at hospital $i$ and $N$ is total samples
4. **Global Update**: Aggregated global model is distributed back to hospitals
5. **Iteration**: Process repeats for multiple rounds until convergence

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## Author

**Eshaan Tushar Bobdey**

*Built with passion for privacy-preserving healthcare AI*
