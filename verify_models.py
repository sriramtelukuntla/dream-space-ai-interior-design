import os
from dotenv import load_dotenv

load_dotenv()

def check_huggingface_token():
    token = os.getenv("HUGGINGFACE_TOKEN")
    if not token:
        print("❌ HUGGINGFACE_TOKEN not found in .env")
        return False

    if not token.startswith("hf_"):
        print("❌ Invalid token format")
        return False

    print("✅ Hugging Face token found")
    return True


def check_model_access():
    from huggingface_hub import HfApi

    token = os.getenv("HUGGINGFACE_TOKEN")
    api = HfApi(token=token)

    models_to_check = [
        "rupeshs/LCM-runwayml-stable-diffusion-v1-5"
    ]

    print("\n🔍 Checking model access...")

    for model_id in models_to_check:
        try:
            api.model_info(model_id)
            print(f"✅ {model_id} - ACCESS OK")
        except Exception as e:
            print(f"❌ {model_id} - ERROR")
            print(str(e))


def test_model_download():
    from huggingface_hub import hf_hub_download

    print("\n📥 Testing model download...")

    try:
        path = hf_hub_download(
            repo_id="runwayml/stable-diffusion-v1-5",
            filename="model_index.json"
        )
        print("✅ Model download test successful")
        print(f"   Cached at: {path}")
        return True
    except Exception as e:
        print("❌ Download failed")
        print(str(e))
        return False


def main():
    print("=" * 60)
    print("🏠 DREAM SPACE: Model Access Verification")
    print("=" * 60)

    if not check_huggingface_token():
        return

    check_model_access()

    if test_model_download():
        print("\n🎉 SUCCESS! All required models accessible")
        print("You can now run: python app.py")
    else:
        print("\n⚠️ Setup incomplete")


if __name__ == "__main__":
    main()
