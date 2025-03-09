from imagekitio import ImageKit

# Initialize ImageKit (Replace with your credentials)
imagekit = ImageKit(
    public_key="public_10G6VDSuQJSnLoUKAyprzW40zSU=",
    private_key="private_gtpcuffnC1Iz/ccE1JpA9b4Hrts=",
    url_endpoint="https://ik.imagekit.io/xenodinger/bubblebliss/",
)


# Function to upload an image and return its URL
def upload_image(file_source):
    try:
        with open(file_source, "rb") as file:
            upload = imagekit.upload_file(file=file, file_name="test-upload.png")

        # Get the uploaded file's URL
        file_url = upload.url
        print("Uploaded File URL:", file_url)
        return file_url
    except Exception as e:
        print("Upload Failed! Error:", str(e))
        return None


# Run the test
if __name__ == "__main__":
    # Ask user for file path
    local_file_path = input("Enter the full path of the image file: ").strip()
    uploaded_file_url = upload_image(local_file_path)
