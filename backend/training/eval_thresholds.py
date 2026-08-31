import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from PIL import ImageFile
import numpy as np
from sklearn.metrics import confusion_matrix, classification_report

ImageFile.LOAD_TRUNCATED_IMAGES = True

TEST_DIR = "cnn_images/test"
BATCH_SIZE = 32
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

val_tf = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

test_ds = datasets.ImageFolder(TEST_DIR, transform=val_tf)
test_dl = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

model = models.resnet18(weights=None)
model.fc = nn.Linear(model.fc.in_features, 2)
model.load_state_dict(torch.load("best_fire_cnn.pth", map_location=DEVICE))
model = model.to(DEVICE)
model.eval()

all_probs = []
all_labels = []

with torch.no_grad():
    for imgs, labels in test_dl:
        imgs = imgs.to(DEVICE)
        outputs = model(imgs)
        probs = torch.softmax(outputs, dim=1)[:, 1].cpu().numpy()
        all_probs.extend(probs)
        all_labels.extend(labels.numpy())

all_probs = np.array(all_probs)
all_labels = np.array(all_labels)

print("=" * 65)
print("  EVALUATION ACROSS DIFFERENT FIRE DETECTION PROBABILITY THRESHOLDS")
print("=" * 65)
print(f"{'Threshold':<12} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'FP (False Alarm)':<18} | {'FN (Missed Fire)':<18}")
print("-" * 80)

for thresh in [0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80]:
    preds = (all_probs >= thresh).astype(int)
    cm = confusion_matrix(all_labels, preds)
    tn, fp, fn, tp = cm.ravel()
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (prec * rec) / (prec + rec) if (prec + rec) > 0 else 0
    print(f"{thresh:<12.2f} | {prec:<10.4f} | {rec:<10.4f} | {f1:<10.4f} | {fp:<18} | {fn:<18}")

print("=" * 65)
