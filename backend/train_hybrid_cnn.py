import torch
import torch.nn as nn
from torchvision import models
import os

class HybridDeforestationCNN(nn.Module):
    def __init__(self):
        super(HybridDeforestationCNN, self).__init__()
        # Using ResNet18 backbone, but overriding the first conv layer 
        # to accept 4 channels instead of 3: (R, G, B, NDVI_SHIFT) or (T1_NDVI, T2_NDVI, Edge, Infrared)
        self.resnet = models.resnet18(weights=None)
        
        # Modify first layer: 4 channels in, 64 out, kernel size 7, stride 2, padding 3
        curr_layer = self.resnet.conv1
        self.resnet.conv1 = nn.Conv2d(4, 64, kernel_size=7, stride=2, padding=3, bias=False)
        
        # Binary Classification
        num_ftrs = self.resnet.fc.in_features
        self.resnet.fc = nn.Sequential(
            nn.Linear(num_ftrs, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 1),
            nn.Sigmoid()
        )

    def forward(self, x):
        return self.resnet(x)

if __name__ == "__main__":
    print("Initializing Hybrid Deforestation CNN (4-channel input)...")
    model = HybridDeforestationCNN()
    
    # Example dummy tensor (Batch Size=8, Channels=4, H=224, W=224)
    dummy_input = torch.randn(8, 4, 224, 224)
    
    out = model(dummy_input)
    print("Output shape:", out.shape) # Expected: [8, 1]
    
    # Save untrained weights as placeholder
    os.makedirs("training", exist_ok=True)
    PATH = "training/hybrid_deforestation_cnn.pth"
    torch.save(model.state_dict(), PATH)
    print(f"Saved initial hybrid model weights to {PATH}")
    print("Ready for custom Dataset training using GEE T1/T2 NDVI layers!")
