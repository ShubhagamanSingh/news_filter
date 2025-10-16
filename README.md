# 📰 AI News Verifier

This Streamlit application is an **AI News Verifier** designed to help students combat misinformation. In an era where fake news spreads rapidly, this tool provides a critical lens to analyze online articles, assess their credibility, and promote media literacy.

## ✨ Features

- **Article Analysis**: Paste text or provide a URL to have an article analyzed by the AI.
- **Credibility Score**: Get a simple 1-10 score to quickly gauge an article's trustworthiness.
- **In-Depth Analysis**: The AI provides a breakdown of the article's tone, bias, use of sources, and potential red flags associated with misinformation.
- **Neutral Summary**: Reads a concise, unbiased summary of the article's key points, helping you understand the core information without the spin.
- **User Authentication**: Secure login and registration system for a personalized experience.
- **Personalized History**: Keeps a log of all your analyzed articles, allowing you to review past results.
- **AI-Powered**: Utilizes a powerful language model (Llama 3) from Hugging Face to provide intelligent and helpful responses.
- **Secure & Private**: Uses Streamlit's secrets management for API tokens and database credentials, and stores user data securely in MongoDB.

## 🚀 Setup and Installation Guide

Follow these steps to get the application running on your local machine.

### Step 1: Get Your Credentials

You will need three things:
1.  **Hugging Face API Token**: To access the AI model.
2.  **MongoDB Connection URI**: To store user data and history.
3.  **Database and Collection Names**: To specify where to store the data in MongoDB.

*   **Hugging Face Token**:
    1.  Go to the Hugging Face website: huggingface.co
    2.  Navigate to **Settings** -> **Access Tokens** and create a new token with `read` permissions.
    3.  Copy the generated token (`hf_...`).

*   **MongoDB URI**:
    1.  Create a free cluster on MongoDB Atlas.
    2.  Once your cluster is set up, go to **Database** -> **Connect** -> **Drivers**.
    3.  Select Python and copy the connection string (URI). Remember to replace `<password>` with your database user's password.
    4.  You will also need to name your database and collection (e.g., `news_verifier_db`, `users`).

### Step 2: Create the Secrets File

Streamlit uses a `.streamlit/secrets.toml` file to store sensitive information like API keys.

1.  In your project's root directory (`news_filter/`), create a new folder named `.streamlit`.
2.  Inside the `.streamlit` folder, create a new file named `secrets.toml`.
3.  Add your credentials to this file as shown below:

    ```toml
    # .streamlit/secrets.toml
    HF_TOKEN = "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    MONGO_URI = "mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority"
    DB_NAME = "your_database_name"
    COLLECTION_NAME = "your_collection_name"
    ```
    *Replace the placeholder values with your actual credentials.*

### Step 3: Install Dependencies

Open your terminal or command prompt, navigate to the project's root directory (`news_filter/`), and run the following command to install the required Python packages:

```bash
pip install -r requirements.txt
```

### Step 4: Run the Streamlit App

Once the installation is complete, run the following command in your terminal:

```bash
streamlit run app.py
```

Your web browser should automatically open with the application running!

## 📁 Project Structure
news_filter/
├── .streamlit/
│   └── secrets.toml
├── app.py
├── requirements.txt
└── README.md

## ⚖️ License

Copyright (c) 2025 Shubhagaman Singh. All Rights Reserved.

This project is licensed under a proprietary license. Unauthorized copying, modification, distribution, or use of this software is strictly prohibited.

See the LICENSE.md file for full details.
