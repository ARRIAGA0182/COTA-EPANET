"""Windows entrypoint and headless dependency test for packaged application."""
import sys
import traceback

def main():
    if "--self-test" in sys.argv:
        try:
            import rasterio
            from rasterio.crs import CRS
            from rasterio.env import Env
            from rasterio.warp import transform
            assert CRS.from_epsg(5482)
            with Env():
                xx, yy = transform("EPSG:4326", "EPSG:5482", [-90.5], [14.6])
                assert len(xx) == len(yy) == 1
            print("COTA NET GIS dependency self-test OK", flush=True)
            return 0
        except Exception:
            traceback.print_exc()
            return 1
    import tkinter as tk
    from integrated_viewer import IntegratedViewer
    root = tk.Tk()
    IntegratedViewer(root)
    root.mainloop()
    return 0

if __name__ == "__main__":
    sys.exit(main())
