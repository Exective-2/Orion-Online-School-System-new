import sys
import subprocess
import importlib

REQUIRED_PACKAGES = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "jwt": "pyjwt",
    "jinja2": "jinja2",
    "multipart": "python-multipart",
    "passlib": "passlib[bcrypt]"
}

def install_and_verify():
    print("Checking dependencies...")
    missing = []
    for module_name, package_name in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            # Special check for python-multipart which registers as 'multipart'
            if module_name == "multipart":
                try:
                    importlib.import_module("multipart")
                    continue
                except ImportError:
                    pass
            # Special check for pyjwt which registers as 'jwt'
            if module_name == "jwt":
                try:
                    importlib.import_module("jwt")
                    continue
                except ImportError:
                    pass
            missing.append(package_name)

    if missing:
        print(f"Installing missing web packages: {', '.join(missing)}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
            print("Dependencies installed successfully!")
        except Exception as e:
            print(f"Error installing packages: {e}")
            sys.exit(1)
    else:
        print("All dependencies are satisfied.")

if __name__ == "__main__":
    install_and_verify()
    
    import uvicorn
    print("\n------------------------------------------------------------")
    print(" Orion School Management System is running in web mode!")
    print(" Access the application at: http://127.0.0.1:8000")
    print("------------------------------------------------------------\n")
    
    # Run the Uvicorn web server
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
