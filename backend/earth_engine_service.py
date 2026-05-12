import ee
import os

def init_gee():
    try:
        # If already initialized, it won't throw
        try:
            ee.Number(1).getInfo()
            return True
        except:
            pass
            
        # Check if service account JSON path is provided in ENV
        gee_key_path = os.getenv("EE_SERVICE_ACCOUNT_JSON")
        if gee_key_path and os.path.exists(gee_key_path):
            print("Initializing Earth Engine via Service Account...")
            credentials = ee.ServiceAccountCredentials('', gee_key_path)
            ee.Initialize(credentials)
            return True
        else:
            print("Initializing Earth Engine via local auth...")
            ee.Initialize(project=os.getenv("EE_PROJECT_ID", "your-project-id"))
            return True
    except Exception as e:
        print(f"GEE Initialization failed: {e}. Please run 'earthengine authenticate' in the terminal.")
        return False

def calculate_ndvi_change(lat, lon, start_date_t1, end_date_t1, start_date_t2, end_date_t2, buffer_m=5000):
    """
    Calculate NDVI for two time periods and determine the shift over a region.
    T1 is the older period, T2 is the newer period.
    Returns the mean NDVI difference (T2 - T1). Negative means vegetation loss.
    """
    if not init_gee():
        return None

    try:
        point = ee.Geometry.Point([lon, lat])
        region = point.buffer(buffer_m)
        
        # helper for NDVI calculation
        def add_ndvi(image):
            ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
            return image.addBands(ndvi)

        # Harmonized Sentinel-2 SR collection
        collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterBounds(region) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
            .map(add_ndvi)
            
        t1_image = collection.filterDate(start_date_t1, end_date_t1).mean().clip(region)
        t2_image = collection.filterDate(start_date_t2, end_date_t2).mean().clip(region)
        
        # Calculate difference (T2 - T1)
        ndvi_diff = t2_image.select('NDVI').subtract(t1_image.select('NDVI')).rename('NDVI_shift')
        
        # Reduce region to get average change
        stats = ndvi_diff.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=10,
            maxPixels=1e9
        )
        
        shift_value = stats.get('NDVI_shift').getInfo()
        return shift_value
    except Exception as e:
        print(f"Error computing NDVI shift for ({lat}, {lon}): {e}")
        return None

def get_ndvi_map_url(lat, lon, start_date, end_date, buffer_m=5000):
    """Generate a thumbnail URL for the NDVI map to return to the frontend."""
    if not init_gee():
        return None

    try:
        point = ee.Geometry.Point([lon, lat])
        region = point.buffer(buffer_m)
        
        def add_ndvi(image):
            ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
            return image.addBands(ndvi)

        collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterBounds(region) \
            .filterDate(start_date, end_date) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
            .map(add_ndvi)
            
        image = collection.mean().clip(region)
        
        url = image.select('NDVI').getThumbURL({
            'dimensions': 512,
            'region': region.bounds(),
            'min': -0.1,
            'max': 0.8,
            'palette': ['red', 'yellow', 'green', 'darkgreen'],
            'format': 'png'
        })
        return url
    except Exception as e:
        print(f"Error getting NDVI thumb: {e}")
        return None
