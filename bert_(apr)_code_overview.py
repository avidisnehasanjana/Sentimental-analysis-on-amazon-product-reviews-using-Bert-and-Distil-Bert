# -*- coding: utf-8 -*-
"""BERT (APR) CODE OVERVIEW.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/10Crz3WQ2jHpoooOUzGMwxUpTFvlI8F5h
"""

import pandas as pd
import re

# Load the dataset
file_path = "Final_UpdatedProductReviews_withRatings.csv"  # Replace with your dataset's file path
data = pd.read_csv(file_path)

# Step 1: Retain relevant columns
cleaned_data = data[['description', 'review_rating']].copy()

# Step 2: Remove rows with missing descriptions
cleaned_data = cleaned_data.dropna(subset=['description'])

# Step 3: Clean and preprocess the text
def preprocess_text(text):
    # Remove special characters, numbers, and extra spaces, convert to lowercase
    text = re.sub(r'[^a-zA-Z\s]', '', text)  # Keep only letters and spaces
    text = text.lower()  # Convert to lowercase
    text = re.sub(r'\s+', ' ', text).strip()  # Remove extra spaces
    return text

cleaned_data['cleaned_description'] = cleaned_data['description'].apply(preprocess_text)

# Step 4: Map review ratings to sentiment labels
def map_sentiment(rating):
    if rating <= 2:
        return 0  # Negative
    elif rating == 3:
        return 1  # Neutral
    else:
        return 2  # Positive

cleaned_data['sentiment_label'] = cleaned_data['review_rating'].apply(map_sentiment)

# Step 5: Keep only the cleaned description and sentiment label columns
final_data = cleaned_data[['cleaned_description', 'sentiment_label']]

# Step 6: Save the cleaned dataset
final_data.to_csv("Cleaned_Reviews.csv", index=False)
print("Cleaned dataset saved as 'Cleaned_Reviews.csv'")

import pandas as pd

# Load the cleaned dataset
cleaned_data = pd.read_csv("Cleaned_Reviews.csv")

# Display basic information and preview the data
print(cleaned_data.info())
print(cleaned_data.head())

pip install transformers

pip install torch

import pandas as pd
import torch
from transformers import BertTokenizer, BertForSequenceClassification
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split

# Load the cleaned data
file_path = "Cleaned_Reviews.csv"  # Make sure to use the correct file path
data = pd.read_csv(file_path)

# Check if data is loaded correctly
print(data.head())
print(data.tail())

from transformers import BertTokenizer


# Load BERT tokenizer
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')


# Tokenize all reviews at once
tokenized_data = tokenizer(
    list(data['cleaned_description']),
    padding=True,
    truncation=True,
    max_length=128,
    return_tensors="pt"
)
print(len(tokenized_data['input_ids']))  # Should match the number of rows in 'data'
print(len(data['sentiment_label']))  # Should match the number of rows in 'data'

from sklearn.model_selection import train_test_split

# Prepare the sentiment labels
y = data['sentiment_label'].values  # These are the sentiment labels (0, 1, 2)

# Convert the tokenized_data into a format that can be split
# Convert tokenized_data to a list of dictionaries
tokenized_list = [{key: value[i] for key, value in tokenized_data.items()} for i in range(len(tokenized_data['input_ids']))]

# Split the data (tokenized_list and labels) consistently
X_train, X_test, y_train, y_test = train_test_split(tokenized_list, y, test_size=0.2, random_state=42)

# Check if the split works as expected
print(len(X_train), len(y_train))  # Should match
print(len(X_test), len(y_test))    # Should match

from torch.utils.data import Dataset

class ReviewDataset(Dataset):
    def __init__(self, tokenized_data, labels):
        self.tokenized_data = tokenized_data
        self.labels = labels

    def __getitem__(self, idx):
        # Extract tokenized data and labels for a single example
        item = self.tokenized_data[idx]
        item['labels'] = torch.tensor(self.labels[idx])
        return item

    def __len__(self):
        return len(self.labels)

from torch.utils.data import DataLoader

# Ensure tokenized data is properly split
# tokenized_data is already split into X_train and X_test
train_dataset = ReviewDataset(X_train, y_train)
test_dataset = ReviewDataset(X_test, y_test)

# Create DataLoaders for training and testing
train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True, num_workers=4)
test_loader = DataLoader(test_dataset, batch_size=128, shuffle=False, num_workers=4)

from torch.cuda.amp import autocast, GradScaler
from torch.utils.data import DataLoader
from transformers import BertForSequenceClassification, AdamW, BertTokenizer
import torch
from tqdm import tqdm

# Check if CUDA is available (GPU)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load pre-trained DistilBERT model for sequence classification
model = BertForSequenceClassification.from_pretrained('bert-base-uncased', num_labels=3)  # 3 labels for sentiment: 0, 1, 2
model.to(device)

# Initialize the optimizer
optimizer = AdamW(model.parameters(), lr=2e-5)

# Gradient scaler for mixed precision
scaler = GradScaler()

# Set the number of epochs
epochs = 2
accumulation_steps = 4  # Accumulate gradients over 4 steps

# Create DataLoader for training and testing
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)  # Adjust batch size as needed
test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)

for epoch in range(epochs):
    model.train()
    total_loss = 0

    # Iterate through batches in training data
    for batch_idx, batch in enumerate(tqdm(train_loader, desc=f"Epoch {epoch+1}")):
        batch = {key: value.to(device) for key, value in batch.items()}

        # Zero gradients
        optimizer.zero_grad()

        # Forward pass with mixed precision
        with autocast():  # Use mixed precision
            outputs = model(**batch)
            loss = outputs.loss

        # Backward pass
        scaler.scale(loss).backward()  # Scales loss for FP16 precision

        # Accumulate gradients for every `accumulation_steps`
        if (batch_idx + 1) % accumulation_steps == 0:
            scaler.step(optimizer)  # Update model parameters
            scaler.update()  # Update the scaler

            # Zero out gradients after step
            optimizer.zero_grad()

        total_loss += loss.item()

    # Print the loss for this epoch
    print(f"Epoch {epoch+1} - Loss: {total_loss / len(train_loader)}")

    # Clear CUDA memory after each epoch (optional, but recommended if you face memory issues)
    torch.cuda.empty_cache()

from sklearn.metrics import accuracy_score, classification_report

# Set the model to evaluation mode
model.eval()

# Initialize lists to store predictions and true labels
all_preds_bert = []
all_labels_bert = []

# Disable gradient computation for evaluation (faster and uses less memory)
with torch.no_grad():
    for batch in tqdm(test_loader, desc="Evaluating"):
        batch = {key: value.to(device) for key, value in batch.items()}
        outputs = model(**batch)

        # Get the predicted labels
        preds = torch.argmax(outputs.logits, dim=1)

        # Store the predictions and true labels
        all_preds_bert.extend(preds.cpu().numpy())
        all_labels_bert.extend(batch['labels'].cpu().numpy())

# Calculate the accuracy
accuracy = accuracy_score(all_labels_bert, all_preds_bert)
print(f"Accuracy: {accuracy * 100:.4f}%")

# Print a classification report
print(classification_report(all_labels_bert, all_preds_bert))



from sklearn.metrics import accuracy_score, classification_report

# Set the model to evaluation mode
model.eval()

# Initialize lists to store predictions and true labels
all_preds_distilbert = []
all_labels_distilbert = []

# Disable gradient computation for evaluation (faster and uses less memory)
with torch.no_grad():
    for batch in tqdm(test_loader, desc="Evaluating"):
        batch = {key: value.to(device) for key, value in batch.items()}
        outputs = model(**batch)

        # Get the predicted labels
        preds = torch.argmax(outputs.logits, dim=1)

        # Store the predictions and true labels
        all_preds_distilbert.extend(preds.cpu().numpy())
        all_labels_distilbert.extend(batch['labels'].cpu().numpy())

# Calculate the accuracy
accuracy = accuracy_score(all_labels_distilbert, all_preds_distilbert)
print(f"Accuracy: {accuracy * 100:.4f}%")

# Print a classification report
print(classification_report(all_labels_distilbert, all_preds_distilbert))

from sklearn.metrics import classification_report
import numpy as np

# Assuming all_labels and all_preds are your true labels and predicted labels
report = classification_report(all_labels, all_preds, output_dict=True)

# Rounding the values to 4 decimal places
for key in report:
    if isinstance(report[key], dict):  # If the entry is a dictionary, round the values
        for subkey in report[key]:
            report[key][subkey] = round(report[key][subkey], 4)

# To print the updated classification report
for key, value in report.items():
    if isinstance(value, dict):
        print(f"{key}:")
        for subkey, subvalue in value.items():
            print(f"  {subkey}: {subvalue:.4f}")
    else:
        print(f"{key}: {value:.4f}")

# Save the model and tokenizer
model.save_pretrained('bert_sentiment_model')  # Save the BERT model
tokenizer.save_pretrained('bert_sentiment_model')  # Save the BERT tokenizer

from transformers import BertForSequenceClassification, BertTokenizer

model = BertForSequenceClassification.from_pretrained('bert_sentiment_model')
tokenizer = BertTokenizer.from_pretrained('bert_sentiment_model')

# Move the model to the same device as the inputs (GPU in this case)
model.to(device)

# Tokenize the new texts
inputs = tokenizer(new_texts, padding=True, truncation=True, max_length=128, return_tensors="pt")

# Move the tokenized inputs to the same device as the model (GPU in this case)
inputs = {key: value.to(device) for key, value in inputs.items()}

# Get predictions from the model
model.eval()
with torch.no_grad():
    outputs = model(**inputs)
    preds = torch.argmax(outputs.logits, dim=1)

# Print the predicted sentiment (0=Negative, 1=Neutral, 2=Positive)
for text, pred in zip(new_texts, preds):
    print(f"Text: {text} | Predicted sentiment: {pred.item()}")

# Example code to take input from the user and predict sentiment

from transformers import BertTokenizer, BertForSequenceClassification
import torch

# Load the trained model and tokenizer
model = BertForSequenceClassification.from_pretrained('bert_sentiment_model')
tokenizer = BertTokenizer.from_pretrained('bert_sentiment_model')

# Set device to GPU if available, otherwise use CPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# Function to predict sentiment
def predict_sentiment(text):
    # Tokenize the input text
    inputs = tokenizer(text, padding=True, truncation=True, max_length=128, return_tensors="pt").to(device)

    # Set the model to evaluation mode
    model.eval()

    # Make prediction
    with torch.no_grad():
        outputs = model(**inputs)
        pred = torch.argmax(outputs.logits, dim=1).item()

    # Map predicted class to sentiment
    sentiment = {0: "Negative", 1: "Neutral", 2: "Positive"}

    return sentiment[pred]

# Take input from the user
user_input = input("Enter a product review: ")

# Predict sentiment
predicted_sentiment = predict_sentiment(user_input)
print(f"Predicted Sentiment: {predicted_sentiment}")

from transformers import BertTokenizer, BertForSequenceClassification
import torch

# Load the trained model and tokenizer
model = BertForSequenceClassification.from_pretrained('bert_sentiment_model')
tokenizer = BertTokenizer.from_pretrained('bert_sentiment_model')

# Set device to GPU if available, otherwise use CPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# Function to predict sentiment
def predict_sentiment(text):
    # Tokenize the input text
    inputs = tokenizer(text, padding=True, truncation=True, max_length=128, return_tensors="pt").to(device)

    # Set the model to evaluation mode
    model.eval()

    # Make prediction
    with torch.no_grad():
        outputs = model(**inputs)
        pred = torch.argmax(outputs.logits, dim=1).item()

    # Map predicted class to sentiment
    sentiment = {0: "Negative", 1: "Neutral", 2: "Positive"}

    return sentiment[pred]

# List of reviews (or sentences)
reviews_list = [
    "I love this product! It's amazing.",
    "This is terrible, very bad experience.",
    "It works okay, but nothing special.",
    "Very disappointed with the quality.",
    "It’s a decent product for the price."
]

# Predict sentiment for each review in the list
for review in reviews_list:
    predicted_sentiment = predict_sentiment(review)
    print(f"Review: {review} | Predicted Sentiment: {predicted_sentiment}")

# from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
# import torch

# # Load the trained model and tokenizer
# model = DistilBertForSequenceClassification.from_pretrained('distilbert_sentiment_model')
# tokenizer = DistilBertTokenizer.from_pretrained('distilbert_sentiment_model')

# Set device to GPU if available, otherwise use CPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# Function to predict sentiment
def predict_sentiment(text):
    # Tokenize the input text
    inputs = tokenizer(text, padding=True, truncation=True, max_length=128, return_tensors="pt").to(device)

    # Set the model to evaluation mode
    model.eval()

    # Make prediction
    with torch.no_grad():
        outputs = model(**inputs)
        pred = torch.argmax(outputs.logits, dim=1).item()

    # Map predicted class to sentiment
    sentiment = {0: "Negative", 1: "Neutral", 2: "Positive"}

    return sentiment[pred]

# List of 100 reviews (including negative, neutral, and positive sentiments)
reviews_list = [
    "I love this product! It's amazing.",
    "This is terrible, very bad experience.",
    "It works okay, but nothing special.",
    "Very disappointed with the quality.",
    "It’s a decent product for the price.",
    "Not great, but it gets the job done.",
    "The item arrived broken. Very frustrating.",
    "I have used better products in this category.",
    "Best purchase ever! Highly recommend it!",
    "It's alright, but could be improved.",
    "The battery life is short. Wouldn't buy again.",
    "Works well, but the design is not great.",
    "I had higher expectations. The quality is average.",
    "Not bad, but I’ve seen better options.",
    "Excellent value for the price. I'm satisfied.",
    "I wouldn’t buy this again. Very disappointed.",
    "This item didn’t meet my expectations at all.",
    "Decent quality, but not worth the price.",
    "This is just an okay product. Nothing extraordinary.",
    "Perfect for my needs, highly recommended!",
    "The packaging was poor. It came damaged.",
    "I’m not sure about this product. It’s decent.",
    "It performs well, but the build quality is weak.",
    "This product does exactly what I wanted.",
    "The service was great, but the product is lacking.",
    "I feel like I wasted my money on this one.",
    "A solid product, but could use more features.",
    "I love the design, but it doesn’t perform well.",
    "I regret buying this. It doesn’t do what it says.",
    "Very happy with this purchase. Totally worth it.",
    "I’m not impressed. The product could be better.",
    "This product exceeded my expectations!",
    "It’s okay, but I expected more for the price.",
    "Very poor quality. I’m returning it.",
    "I have no complaints, works as expected.",
    "Meh, it’s an average product.",
    "This product has a lot of potential but is underwhelming.",
    "The quality is decent, but the price is too high.",
    "It works, but it’s nothing special.",
    "Could be better, but it’s not bad.",
    "Slightly disappointed. It doesn’t match the description.",
    "The product is fine, but I expected something more durable.",
    "I’m really impressed by how well it works!",
    "The material feels cheap, not what I expected.",
    "It serves its purpose, but doesn’t blow me away.",
    "This is my second time purchasing this, love it!",
    "I’m unimpressed with the performance of this product.",
    "The reviews were misleading. This product doesn’t perform well.",
    "Good, but not perfect.",
    "I don’t regret the purchase, but I’m not wowed either.",
    "I like it, but I think the price is a bit high.",
    "This was a waste of money.",
    "The product is okay, but doesn’t have any standout features.",
    "I would recommend this if you need a basic product.",
    "Works as advertised, but there are better alternatives.",
    "It’s a solid product for the price range.",
    "Good product overall, but there were a few issues.",
    "Wouldn't buy again, not worth it.",
    "Great for the price, but not amazing.",
    "The product looks good, but it’s not performing well.",
    "This is a great buy if you’re looking for something simple.",
    "The functionality is good, but the durability is poor.",
    "This product does its job, but there are better options out there.",
    "The build quality is disappointing. Feels cheap.",
    "It's very easy to use, but doesn’t have the features I wanted.",
    "It’s fine, but I wouldn’t recommend it.",
    "The product arrived late and was not as described.",
    "The customer service was good, but the product wasn’t.",
    "I’m not impressed with how it performs.",
    "This was an okay purchase, but I wouldn’t recommend it.",
    "The product is functional, but not impressive.",
    "The color is not what I expected, and it’s a bit flimsy.",
    "It’s a decent product, but nothing extraordinary.",
    "It works fine, just not as durable as I had hoped.",
    "I love this product, it’s exactly what I needed.",
    "This product didn’t live up to the hype.",
    "It’s a solid option, but could be improved.",
    "It does the job, but I don’t think it’s worth the price.",
    "The functionality is decent, but I expected better quality.",
    "This product didn’t meet my expectations, I’m returning it.",
    "I’m impressed with how well it works, great purchase.",
    "Not very durable, but it works for now.",
    "The product works well but looks cheaply made.",
    "I expected more, but it’s still an okay product.",
    "Very poor quality for the price.",
    "The product is decent but could use improvements.",
    "I’m happy with the performance but not with the design.",
    "Good product but not very user-friendly.",
    "This is a good purchase, but I think it could be cheaper.",
    "This product is good for the price, but nothing special.",
    "The product is okay, but I feel like I overpaid.",
    "I wouldn’t buy this again, but it works fine for now.",
    "Good product, but it’s a bit overpriced for the quality.",
    "The quality is lacking, but it serves its purpose.",
    "The product is fine, but I’m not overly impressed.",
    "Doesn’t perform as expected, quite disappointed.",
    "I expected more for the price. It's just average.",
    "It’s a decent product, but I don’t think I’ll buy it again.",
    "The product works well but looks poorly designed.",
    "I'm satisfied with the purchase but not thrilled.",
    "I like it, but I expected better quality for the price.",
    "The product does its job, but it’s nothing special.",
    "Good product overall, but the quality could be improved.",
    "The product works, but I’ve had better experiences elsewhere.",
    "It’s an okay product but not great.",
    "Could have been better, but it’s not terrible.",
    "I love the performance, but the quality is lacking.",
    "It works well, but I don’t think it’s worth the price.",
    "Good, but not great. Could be improved.",
    "This product is just okay. I would not buy again.",
    "Not what I expected, but still decent.",
    "It’s a decent product, but I expected better quality.",
    "It’s a good product, but not perfect.",
    "The quality of this product is really low.",
    "It does its job, but the quality isn’t great.",
    "The product broke after a few uses.",
    "This product is disappointing. Not as good as I thought it would be.",
]

# Predict sentiment for each review in the list
for review in reviews_list:
    predicted_sentiment = predict_sentiment(review)
    print(f"Review: {review} | Predicted Sentiment: {predicted_sentiment}")

from sklearn.metrics import confusion_matrix
import seaborn as sns
import matplotlib.pyplot as plt

# Get the confusion matrix
cm = confusion_matrix(all_labels, all_preds)

# Plot the confusion matrix
plt.figure(figsize=(6, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['Negative', 'Neutral', 'Positive'], yticklabels=['Negative', 'Neutral', 'Positive'])
plt.xlabel('Predicted')
plt.ylabel('True')
plt.title('Confusion Matrix')
plt.show()

from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# Assuming the true labels and predictions for both models are already available
# Example:
# all_labels_bert, all_preds_bert  # for BERT model
# all_labels_distilbert, all_preds_distilbert  # for DistilBERT model

# Compute confusion matrices
cm_bert = confusion_matrix(all_labels_bert, all_preds_bert)
cm_distilbert = confusion_matrix(all_labels_distilbert, all_preds_distilbert)

# Calculate Precision, Recall, and F1-Score for both models
def compute_metrics(cm):
    # We assume the labels are ['Negative', 'Neutral', 'Positive']
    precision, recall, fscore, _ = precision_recall_fscore_support(
        cm.argmax(axis=1), cm.argmax(axis=0), average=None
    )
    return precision, recall, fscore

precision_bert, recall_bert, fscore_bert = compute_metrics(cm_bert)
precision_distilbert, recall_distilbert, fscore_distilbert = compute_metrics(cm_distilbert)

# Set up categories
categories = ['Negative', 'Neutral', 'Positive']

# Create bar plot comparison for Precision, Recall, and F1-Score
x = np.arange(len(categories))  # the label locations
width = 0.35  # the width of the bars

fig, ax = plt.subplots(figsize=(10, 6))

# Bars for Precision, Recall, and F1-Score for BERT and DistilBERT
bar1 = ax.bar(x - width/2, precision_bert, width, label='BERT Precision', color='royalblue')
bar2 = ax.bar(x + width/2, precision_distilbert, width, label='DistilBERT Precision', color='darkorange')

bar3 = ax.bar(x - width/2, recall_bert, width, label='BERT Recall', color='lightblue', alpha=0.7)
bar4 = ax.bar(x + width/2, recall_distilbert, width, label='DistilBERT Recall', color='orange', alpha=0.7)

bar5 = ax.bar(x - width/2, fscore_bert, width, label='BERT F1-Score', color='dodgerblue', alpha=0.5)
bar6 = ax.bar(x + width/2, fscore_distilbert, width, label='DistilBERT F1-Score', color='darkred', alpha=0.5)

ax.set_xlabel('Categories')
ax.set_ylabel('Scores')
ax.set_title('Model Comparison: BERT vs DistilBERT')
ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.legend()

# Display the plot
plt.show()