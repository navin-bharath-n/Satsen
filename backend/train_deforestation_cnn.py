import os
import torch
import torch.nn as nn
from torchvision import models, transforms
from torch.utils.data import Dataset, DataLoader
from PIL import Image, ImageDraw
import numpy as np

# ==========================================================
# SYNTHETIC DEFORESTATION DATASET
# Generates realistic-looking "Before & After" NDVI-style images
# Label 0: Healthy Forest (High vegetation)
# Label 1: Deforested (Brown/Barren patches)
# ==========================================================

class SyntheticDeforestationDataset(Dataset):
    def __init__(self, num_samples=1000, transform=None):
        self.num_samples = num_samples
        self.transform = transform
        
        # 50% healthy, 50% deforested
        self.labels = [0 if i < num_samples // 2 else 1 for i in range(num_samples)]
        
    def __len__(self):
        return self.num_samples
        
    def generate_image(self, label):
        # Create a base green image (Healthy Forest)
        img = Image.new('RGB', (128, 128), color=(34, 139, 34)) # Forest Green
        draw = ImageDraw.Draw(img)
        
        # Add some texture/noise (Trees)
        for _ in range(200):
            x = np.random.randint(0, 128)
            y = np.random.randint(0, 128)
            r = np.random.randint(2, 6)
            shade = np.random.randint(20, 100)
            draw.ellipse([x, y, x+r, y+r], fill=(0, shade, 0))
            
        if label == 1:
            # Deforested: Add brown/barren patches (Logging roads, clearing)
            num_patches = np.random.randint(1, 4)
            for _ in range(num_patches):
                x = np.random.randint(10, 100)
                y = np.random.randint(10, 100)
                w = np.random.randint(20, 60)
                h = np.random.randint(20, 60)
                draw.rectangle([x, y, x+w, y+h], fill=(139, 69, 19)) # SaddleBrown
                
                # Add logging road
                draw.line([(0, np.random.randint(0,128)), (128, np.random.randint(0,128))], fill=(210, 180, 140), width=np.random.randint(4, 10))
                
        return img

    def __getitem__(self, idx):
        label = self.labels[idx]
        img = self.generate_image(label)
        
        if self.transform:
            img = self.transform(img)
            
        return img, torch.tensor([float(label)])

# ==========================================================
# MODEL DEFINITION (ResNet18)
# ==========================================================
class DeforestationResNet(nn.Module):
    def __init__(self):
        super(DeforestationResNet, self).__init__()
        # Use a pre-trained ResNet18 for powerful feature extraction
        self.resnet = models.resnet18(pretrained=True)
        num_ftrs = self.resnet.fc.in_features
        
        # Replace the classifier for our binary task (0 to 1 probability)
        self.resnet.fc = nn.Sequential(
            nn.Linear(num_ftrs, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.resnet(x)

def train_model():
    print("🌲 Generating Synthetic Deforestation Dataset...")
    
    transform = transforms.Compose([
        transforms.Resize((128, 128)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    # 1000 Train, 200 Val
    train_dataset = SyntheticDeforestationDataset(num_samples=1000, transform=transform)
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🖥️ Using device: {device}")
    
    model = DeforestationResNet().to(device)
    criterion = nn.BCELoss() # Binary Cross Entropy for Sigmoid
    optimizer = torch.optim.Adam(model.parameters(), lr=0.0005)
    
    print("🚀 Starting Training Loop (ResNet18)...")
    epochs = 5
    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        
        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            
            # Calculate accuracy
            predicted = (outputs > 0.5).float()
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
        epoch_loss = running_loss / len(train_loader)
        epoch_acc = 100 * correct / total
        print(f"Epoch [{epoch+1}/{epochs}] - Loss: {epoch_loss:.4f} - Accuracy: {epoch_acc:.2f}%")
        
    os.makedirs("training", exist_ok=True)
    save_path = "training/deforestation_resnet.pth"
    torch.save(model.state_dict(), save_path)
    print(f"✅ Deforestation Model saved to {save_path}")

if __name__ == "__main__":
    train_model()
