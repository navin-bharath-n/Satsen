import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from PIL import ImageFile
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report, confusion_matrix
import numpy as np

# ======================
# SAFETY FIX (corrupted images)
# ======================
ImageFile.LOAD_TRUNCATED_IMAGES = True

# ======================
# PATHS
# ======================
TRAIN_DIR = "cnn_images/train"
VAL_DIR   = "cnn_images/valid"
TEST_DIR  = "cnn_images/test"

# ======================
# CONFIG
# ======================
BATCH_SIZE = 16
EPOCHS = 10
LR = 1e-4
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("🔥 Training on:", DEVICE)

# ======================
# TRANSFORMS (OPTIMIZED FOR RESNET18)
# ======================
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]

# Using standard 224x224 to leverage Pre-trained ResNet18 features fully
train_tf = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
    transforms.ToTensor(),
    transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
])

val_tf = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
])

# ======================
# DATASETS
# ======================
train_ds = datasets.ImageFolder(TRAIN_DIR, transform=train_tf)
val_ds   = datasets.ImageFolder(VAL_DIR, transform=val_tf)
test_ds  = datasets.ImageFolder(TEST_DIR, transform=val_tf)

print("✅ Classes:", train_ds.classes)

# ======================
# DATALOADERS (Windows safe)
# ======================
train_dl = DataLoader(
    train_ds,
    batch_size=BATCH_SIZE,
    shuffle=True,
    num_workers=0,
    pin_memory=True
)

val_dl = DataLoader(
    val_ds,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=0,
    pin_memory=True
)

test_dl = DataLoader(
    test_ds,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=0,
    pin_memory=True
)

# ======================
# MODEL (TRANSFER LEARNING)
# ======================
weights = models.ResNet18_Weights.DEFAULT
model = models.resnet18(weights=weights)

# Binary classification: wildfire / nowildfire
model.fc = nn.Linear(model.fc.in_features, 2)
model = model.to(DEVICE)

# ======================
# TRAINING SETUP
# ======================
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=LR)

# History tracking for visualization
history = {
    "train_loss": [],
    "train_acc": [],
    "val_loss": [],
    "val_acc": []
}

best_val_acc = 0.0

# ======================
# TRAIN LOOP
# ======================
for epoch in range(EPOCHS):
    model.train()
    train_correct = 0
    train_total = 0
    running_loss = 0.0

    for imgs, labels in train_dl:
        imgs = imgs.to(DEVICE)
        labels = labels.to(DEVICE)

        outputs = model(imgs)
        loss = criterion(outputs, labels)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * imgs.size(0)
        preds = outputs.argmax(dim=1)
        train_correct += (preds == labels).sum().item()
        train_total += labels.size(0)

    epoch_train_loss = running_loss / train_total
    epoch_train_acc = train_correct / train_total

    # ======================
    # VALIDATION
    # ======================
    model.eval()
    val_correct = 0
    val_total = 0
    val_running_loss = 0.0

    with torch.no_grad():
        for imgs, labels in val_dl:
            imgs = imgs.to(DEVICE)
            labels = labels.to(DEVICE)

            outputs = model(imgs)
            loss = criterion(outputs, labels)
            
            val_running_loss += loss.item() * imgs.size(0)
            preds = outputs.argmax(dim=1)

            val_correct += (preds == labels).sum().item()
            val_total += labels.size(0)

    epoch_val_loss = val_running_loss / val_total
    epoch_val_acc = val_correct / val_total

    # Record history
    history["train_loss"].append(epoch_train_loss)
    history["train_acc"].append(epoch_train_acc)
    history["val_loss"].append(epoch_val_loss)
    history["val_acc"].append(epoch_val_acc)

    print(
        f"Epoch {epoch+1:02d}/{EPOCHS:02d} | "
        f"Train Loss: {epoch_train_loss:.4f} | "
        f"Train Acc: {epoch_train_acc:.4f} | "
        f"Val Loss: {epoch_val_loss:.4f} | "
        f"Val Acc: {epoch_val_acc:.4f}"
    )

    # Save best model checkpoint
    if epoch_val_acc > best_val_acc:
        best_val_acc = epoch_val_acc
        torch.save(model.state_dict(), "best_fire_cnn.pth")
        print(f"🌟 Best model saved with Val Acc: {best_val_acc:.4f}")

# ======================
# PLOT TRAINING HISTORY
# ======================
epochs_range = range(1, EPOCHS + 1)
plt.figure(figsize=(12, 5))

# Plot Loss
plt.subplot(1, 2, 1)
plt.plot(epochs_range, history["train_loss"], label="Train Loss", color="royalblue", marker="o")
plt.plot(epochs_range, history["val_loss"], label="Val Loss", color="orange", marker="x")
plt.xlabel("Epoch")
plt.ylabel("Loss")
plt.title("Loss Curve")
plt.legend()
plt.grid(True)

# Plot Accuracy
plt.subplot(1, 2, 2)
plt.plot(epochs_range, history["train_acc"], label="Train Acc", color="royalblue", marker="o")
plt.plot(epochs_range, history["val_acc"], label="Val Acc", color="orange", marker="x")
plt.xlabel("Epoch")
plt.ylabel("Accuracy")
plt.title("Accuracy Curve")
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.savefig("training_metrics.png", dpi=300)
print("📊 training_metrics.png saved successfully")

# ======================
# DETAILED EVALUATION ON TEST SET
# ======================
print("\n🔍 Running detailed evaluation on the Test set...")
# Load the best model weights for evaluation
if best_val_acc > 0.0:
    model.load_state_dict(torch.load("best_fire_cnn.pth", map_location=DEVICE))
    print("✅ Loaded best model weights for test evaluation")

model.eval()
test_preds = []
test_targets = []

with torch.no_grad():
    for imgs, labels in test_dl:
        imgs = imgs.to(DEVICE)
        outputs = model(imgs)
        preds = outputs.argmax(dim=1).cpu().numpy()
        
        test_preds.extend(preds)
        test_targets.extend(labels.numpy())

# Performance Metrics Report
print("\n📊 CLASSIFICATION PERFORMANCE REPORT:")
print(classification_report(test_targets, test_preds, target_names=train_ds.classes))

# Confusion Matrix
print("📉 CONFUSION MATRIX:")
print(confusion_matrix(test_targets, test_preds))

# ======================
# SAVE FINAL MODEL WEIGHTS
# ======================
torch.save(model.state_dict(), "fire_cnn.pth")
print("\n✅ fire_cnn.pth saved successfully")
