# 📄 README.md

# # Review Classifier (Milestone II)

# Review Classifier is a system built with **Flask + scikit-learn + Python scripts** to classify clothing reviews as recommended or not recommended.

# It was developed as **Milestone II** of the assignment, extending Milestone I by training multiple models, exporting them as an ensemble, and integrating into a full Flask Web UI.

# ---

# ## ✨ Features

# - 📝 Train multiple models (Count+LR, TFIDF+LR, TFIDF+SVD+LR).
# - 🤝 Combine them into an **ensemble bundle** (`model/ensemble.pkl`).
# - 📦 Export a **manifest.json** with metadata (weights, tokenizer).
# - 🌐 Flask Web UI:
#   - Predict recommendation from new reviews (`/predict`).
#   - Add new reviews interactively (`/new`).
#   - Visualize metrics (`/metrics`).
#   - Search products by categories (`/search`).
#   - Pagination for large results.
# - 🗂 Generate a JSON catalog (`data/site_items.json`) for keyword + category search.

# ---

# ## ⚙️ Requirements

# - Python **3.9+** (tested with 3.12).
# - pip + venv.
# - Git.

# ---

# ## 🚀 Setup Guide

# ### 1. Clone the repository
# ```bash
# git clone https://github.com/<your-username>/review-classifier.git
# cd review-classifier
# ```

# ### 2. Setup Virtual Environment

# On Mac/Linux:
# ```bash
# python3 -m venv .venv
# source .venv/bin/activate
# ```

# On Windows (PowerShell):
# ```powershell
# python -m venv .venv
# .venv\Scripts\activate
# ```

# ### 3. Install dependencies
# ```bash
# pip install --upgrade pip
# pip install -r requirements.txt
# ```

# ### 4. Train Models with Notebook
# Open Jupyter Notebook:
# ```bash
# jupyter notebook notebooks/milestone2.ipynb
# ```
# Run all cells to:
# - Analyze dataset.
# - Train 3 models.
# - Save bundle (`model/ensemble.pkl`).
# - Generate `data/site_items.json`.

# ### 5. Run the Flask App

# Mac/Linux:
# ```bash
# flask run
# ```

# Windows (PowerShell):
# ```powershell
# set FLASK_APP=app
# set FLASK_ENV=development
# flask run
# ```

# 👉 Now open: http://127.0.0.1:5000/

# ---

# 🗂 Project Structure

# review-classifier/
# ├── app/
# │   ├── controllers/   # Flask routes (main, search)
# │   ├── templates/     # HTML templates (predict.html, new_review.html, metrics.html, search.html, base.html)
# │   ├── static/        # CSS, JS, assets
# │   └── __init__.py
# ├── model/             # Trained ensemble bundle (.pkl + manifest.json)
# ├── data/              # Dataset + generated catalog (assignment3_II.csv, site_items.json)
# ├── notebooks/         # Jupyter notebook for Milestone II
# ├── requirements.txt
# └── README.md

# ---

# ## 📊 Dataset

# Using the **Women’s E-Commerce Clothing Reviews** dataset with columns:
# - `Clothing ID`
# - `Age`
# - `Title`
# - `Review Text`
# - `Rating`
# - `Recommended IND` (target label)
# - `Division Name`
# - `Department Name`
# - `Class Name`

# In Milestone II we focus on:
# - Training models on **Review Text**.
# - Using **categories** (`Rating`, `Division`, `Department`, `Class`) for search and filtering in UI.

# ---

# ## 📈 Models

# - **CountVectorizer + Logistic Regression**
# - **TF-IDF + Logistic Regression**
# - **TF-IDF + SVD (LSA) + Logistic Regression**
# - **Ensemble (equal weights)**

# Metrics evaluated:
# - Accuracy
# - F1 score
# - ROC-AUC

