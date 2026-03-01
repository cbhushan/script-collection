'''
This is a casual (non-academic) meme classification approach that leverages
CLIP and OCR models. This can be used as WhatsApp cleaner!

WhatsApp cleaner: I was motivated to try this in order to cleanup my
WhatsApp media folder that has >20K photos and taking up substantial space
on my phone. A large portion of these photos are memes and other commonly
forwarded images. This prioritizes low false +ve rates, over false -ves.
This approach assumes that whatsapp photos can be accessed
on laptop/desktop where this script will run and users know how to delete
identified files on phone (easiest - a bi-direction sync setup between phone
and the laptop/desktop; something like syncthing).

Steps:
  - Run python whatsapp_cleaner.py /path/to/whatsapp/media  /path/to/tmp/review
  - review folder will following files.
    - symlink to detected meme files. Use thumnail view to verify classification.
    - meme_candidates.txt: absolute path to files classifed as memes. To actually
      delete files run `xargs -a meme_candidates.txt rm`
    - classification_dashbaord.html: HTML dashboard showing classification & scores.
    - classification_report.csv: csv form of classification_dashbaord.html
    - ocr_text_fraction.pklz: File with OCR text-fraction results. OCR is slowest
      step; useful for caching when
  - Review thumbnails and dashboard. Then
    - If things look good: `xargs -a meme_candidates.txt rm`
    - Tweak CLIP prompts (label variable below)
    - Tweak other thresholds

Environment:
    - Started with empty miniforge python 3.12.12 environment.
    - Then: pip install torch torchvision open_clip_torch pillow tqdm

Copyright 2026. C Bhushan; Licensed under the Apache License v2.0.
https://github.com/cbhushan/script-collection

Credits: Bits & pieces of this code was generated using
ChatGPT and Google (AI Mode).
'''
import os
import shutil
import torch
import open_clip
from PIL import Image
from tqdm import tqdm
import imagehash
import csv
import traceback
from pathlib import Path
from pprint import pprint
import numpy as np
from PIL import Image, ImageEnhance
import easyocr
import pickle
import argparse


def rm_target_using_ref(ref_root, target_root):
    """
    Delete files from target_root if the corresponding files are present
    in ref_root.
    - travers files recursively on ref_root
    - computes its relative path wrt ref_root
    - if corresponding relative path wrt target_root exists, it is deleted.
    - folders are skipped and not deleted.
    """
    count = 0
    for root, dirs, files in os.walk(ref_root):
        for file in files:
            # Get the full path of the file in ref_root
            ref_file_path = os.path.join(root, file)

            # Get relative path from ref_root
            rel_path = os.path.relpath(ref_file_path, ref_root)

            # Construct corresponding path in target_root
            target_file_path = os.path.join(target_root, rel_path)

            # Delete if it exists
            if os.path.exists(target_file_path) and os.path.isfile(target_file_path):
                os.remove(target_file_path)
                os.remove(ref_file_path)
                count+= 1
    return count


def delete_empty_dir_recursively(root_path):
    """
    Recursively looks for empty directories and deletes them.
    If a directories becomes empty b/c of such deletion it should also be deleted.
    """
    # Walk from bottom-up to process child directories first
    for root, dirs, files in os.walk(root_path, topdown=False):
        # Only process subdirectories
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                # Check if directory is empty and delete it
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as e:
                print(f"Error deleting {dir_path}:")
                traceback.print_exc()


#
parser = argparse.ArgumentParser(
    description="WhatsApp-type meme classifier with CLIP + OCR"
)

parser.add_argument(
    "source_dir",
    type=str,
    help="Path to (WhatsApp) images directory (recursive scan)"
)

parser.add_argument(
    "review_dir",
    type=str,
    help="Directory where symlinks and reports will be created."
)

parser.add_argument(
    "--proceed-to-delete",
    action="store_true",
    help="If set, deletes files from SOURCE_DIR that match meme candidates in REVIEW_DIR"
)

# ====== CONFIG ======
BATCH_SIZE = 32    # depends on GPU VRAM
THRESHOLD = 0.05   # margin b/w meme- & photo-similarity; Use conservative thresholds
MIN_TEXT_RATIO = 0.13  # OCR area ratio threshold for text

# CLIP prompts for two classes; max of prediction-score across any of the prompt-in-class is used.
labels = {
    "memes": [
        "An infographic or document-style image with a lot of text",
        "A digital flyer with informational text and religious or holiday greetings",
        "A screenshot of a text message or chat conversation",
        "An image with overlaid text or emoji on a character or scene",
        "A humorous digital graphic meant for social media",
        "An image with qr code",
        "A photograph of newspaper",
        "A screenshot of an app on smartphone",
    ],
    "photo": [
        "A candid photograph of a family together",
        "A photogram of a person or people in a domestic setting",
        "A personal photo of a person taken with a smartphone",
        "A group of friends or family posing for a picture",
    ]
}

# ====================

args = parser.parse_args()
SOURCE_DIR = os.path.abspath(args.source_dir)
REVIEW_DIR = os.path.abspath(args.review_dir)
os.makedirs(REVIEW_DIR, exist_ok=True)


# Delete files if --proceed-to-delete flag is set
if args.proceed_to_delete:
    print(f"Assuming that {REVIEW_DIR=} is revied and verified.")
    print(f"Proceeding to delete meme files from {SOURCE_DIR=}")
    n_files = rm_target_using_ref(REVIEW_DIR, SOURCE_DIR)
    print(f"Deleted {n_files} matching files")
    delete_empty_dir_recursively(REVIEW_DIR)
    exit(0)


report_path = os.path.join(REVIEW_DIR, "meme_candidates.txt")  # path to files classifed as memes
csv_path = os.path.join(REVIEW_DIR, "classification_report.csv")  # csv with scores etc.
html_path = os.path.join(REVIEW_DIR, "classification_dashbaord.html")

# file with text-fraction calculation; can be cached to fine-tune text prompts
ocr_result_file = os.path.join(REVIEW_DIR, "ocr_text_fraction.pklz")

# ---- Clean old symlinks from REVIEW_DIR recursively ----
for root, dirs, files in os.walk(REVIEW_DIR):
    for entry in files + dirs:
        full_path = os.path.join(root, entry)

        # Remove only symbolic links
        if os.path.islink(full_path):
            os.unlink(full_path)
delete_empty_dir_recursively(REVIEW_DIR)

device = "cuda" if torch.cuda.is_available() else "cpu"

# ------------------ OCR ------------------
reader = easyocr.Reader(["en"], gpu=torch.cuda.is_available())

# ------------------ Utilities ------------------
def preprocess_image(img_path):
    img = Image.open(img_path).convert("RGB")
    img = img.resize((224, 224))
    # Auto-contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.2)
    # Brightness normalize
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.1)
    return img

def text_area_ratio(img):
    img = np.asarray(img)
    total_area = img.shape[0] * img.shape[1]
    if total_area < 2:  # ~ 1 px!
        return 0

    results = reader.readtext(img)
    total_text_area = 0
    for b in results:
        points = b[0]
        width = points[1][0] - points[0][0]
        height = points[2][1] - points[1][1]
        total_text_area += width * height

    txt_faction = total_text_area / total_area
    return txt_faction

def get_ocr_results(img_paths, cache_file):
    """Compute ocr txt fraction and cache it"""
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as file:
            txt_frac = pickle.load(file)
    else:
        txt_frac = {}

    for path in tqdm(img_paths):
        if path not in txt_frac:
            img = preprocess_image(path)
            txt_frac[path] = text_area_ratio(img)

    with open(cache_file, 'wb') as file:
        pickle.dump(txt_frac, file)
    return txt_frac


def generate_html_dashboard(csv_file, out_html):
    rows = []
    with open(csv_file, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>WhatsApp Meme Classification Dashboard</title>
<style>
body {{
    font-family: Arial, sans-serif;
    background-color: #f5f5f5;
}}
table {{
    border-collapse: collapse;
    width: 100%;
}}
th, td {{
    border: 1px solid #ddd;
    padding: 8px;
    text-align: center;
}}
th {{
    background-color: #333;
    color: white;
    cursor: pointer;
}}
tr:nth-child(even) {{ background-color: #fafafa; }}
tr.meme_candidate {{ background-color: #ffe6e6; }}
img {{
    max-width: 150px;
    max-height: 150px;
}}
</style>
</head>
<body>

<h2>WhatsApp Meme Classification Dashboard</h2>
<p>Total Images: {len(rows)}</p>

<table id="dataTable">
<thead>
<tr>
<th>Image</th>
<th>Decision</th>
<th>Text fraction</th>
<th>Meme Score</th>
<th>Photo Score</th>
<th>Margin</th>
</tr>
</thead>
<tbody>
"""

    for row in rows:
        image_path = Path(row["image_path"]).as_uri()
        decision = row["label_decision"]

        html += f"""
<tr class="{decision}">
<td><img src="{image_path}"></td>
<td>{decision}</td>
<td>{row['text_ratio']}</td>
<td>{row['meme_score']}</td>
<td>{row['photo_score']}</td>
<td>{row['margin']}</td>
</tr>
"""

    html += """
</tbody>
</table>

<script>
// Simple column sorting
document.querySelectorAll("th").forEach((header, index) => {
    header.addEventListener("click", () => {
        const table = header.closest("table");
        const rows = Array.from(table.querySelectorAll("tbody tr"));
        const asc = header.classList.toggle("asc");
        rows.sort((a, b) => {
            const A = a.children[index].innerText;
            const B = b.children[index].innerText;
            return asc ? A.localeCompare(B, undefined, {numeric: true})
                       : B.localeCompare(A, undefined, {numeric: true});
        });
        rows.forEach(row => table.querySelector("tbody").appendChild(row));
    });
});
</script>

</body>
</html>
"""

    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)

    print("Dashboard generated:", out_html)

    return html


# Use the explicit quickgelu variant name
model_name = 'ViT-B-32-quickgelu'
model, _, preprocess = open_clip.create_model_and_transforms(
    model_name, pretrained='openai'
)

model = model.to(device)
model.eval()
tokenizer = open_clip.get_tokenizer(model_name)


# CLIP needs a flat list of prompts
flat_labels = []
label_group_indices = {}

start_idx = 0
for group_name, prompts in labels.items():
    flat_labels.extend(prompts)
    end_idx = start_idx + len(prompts)
    label_group_indices[group_name] = (start_idx, end_idx)
    start_idx = end_idx
pprint(flat_labels)
pprint(label_group_indices)

text_tokens = tokenizer(flat_labels).to(device)
with torch.no_grad():
    text_features = model.encode_text(text_tokens)
    text_features /= text_features.norm(dim=-1, keepdim=True)

def is_duplicate(img_path, hash_dict):
    try:
        img = Image.open(img_path).convert("RGB")
        ph = imagehash.phash(img)
        if ph in hash_dict:
            return True
        hash_dict[ph] = img_path
        return False

    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        return False

# get all image files
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
all_images = []
for root, dirs, files in os.walk(SOURCE_DIR):
    for file in files:
        ext = os.path.splitext(file)[1].lower()
        if ext in IMAGE_EXTENSIONS:
            full_path = os.path.join(root, file)
            all_images.append(full_path)

print(f"Found total image files: {len(all_images)}")

# # Duplicate detection
# print("Scanning for duplicates...")
# hash_dict = {}

# unique_images = []
# for img_path in tqdm(all_images):
#     if not is_duplicate(img_path, hash_dict):
#         unique_images.append(img_path)

unique_images = all_images
print(f"Unique images: {len(unique_images)}")

# for logging
report_file = open(report_path, "w")
csv_file = open(csv_path, "w", newline="")
csv_writer = csv.writer(csv_file)
csv_writer.writerow([
    "image_path",
    "meme_score",
    "photo_score",
    "margin",
    "label_decision",
    "text_ratio"])


# Batch classification
def process_batch(batch_paths, txt_frac):
    images = []
    valid_paths = []

    for path in batch_paths:
        try:
            img = preprocess_image(path)
            images.append(preprocess(img))
            valid_paths.append(path)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            print(f"exception occurred: {path}")
            traceback.print_exc()

    if not images:
        return []

    image_input = torch.stack(images).to(device)

    with torch.no_grad():
        image_features = model.encode_image(image_input)
        image_features /= image_features.norm(dim=-1, keepdim=True)
        similarity = image_features @ text_features.T

    similarity = similarity.cpu().numpy()
    margin_list = []
    for i, path in enumerate(valid_paths):

        meme_start, meme_end = label_group_indices["memes"]
        photo_start, photo_end = label_group_indices["photo"]

        meme_score_arr = similarity[i][meme_start:meme_end]
        photo_score_arr = similarity[i][photo_start:photo_end]
        meme_score = float(meme_score_arr.max())
        photo_score = float(photo_score_arr.max())

        margin = meme_score - photo_score
        margin_list.append(margin)

        # OCR text detection
        if path in txt_frac:
            text_ratio = txt_frac[path]
        else:
            text_ratio = text_area_ratio(preprocess_image(path))

        # Decision: meme if margin > THRESHOLD OR text_ratio > MIN_TEXT_RATIO
        decision = "meme_candidate" if (margin > THRESHOLD or text_ratio > MIN_TEXT_RATIO) else "keep"

        # Write to CSV
        csv_writer.writerow([
            path,
            np.array2string(meme_score_arr, precision=4, floatmode='fixed'), #round(meme_score, 4),
            np.array2string(photo_score_arr, precision=4, floatmode='fixed'), # round(photo_score, 4),
            round(margin, 4),
            decision,
            round(text_ratio, 4),
        ])

        if decision == "meme_candidate":
            # Get relative path from SOURCE_DIR
            rel_path = os.path.relpath(path, SOURCE_DIR)
            symlink_path = os.path.join(REVIEW_DIR, rel_path)

            # Create parent directories if needed
            symlink_dir = os.path.dirname(symlink_path)
            os.makedirs(symlink_dir, exist_ok=True)

            os.symlink(path, symlink_path)
            report_file.write(path + "\n")

    return margin_list


print("ocr computing / caching...")
txt_frac = get_ocr_results(unique_images, ocr_result_file)

print("Classifying images...")
margin_all = []
for i in tqdm(range(0, len(unique_images), BATCH_SIZE)):
    batch = unique_images[i:i+BATCH_SIZE]
    margin_all = margin_all + process_batch(batch, txt_frac)

report_file.close()
csv_file.close()


# stats of actual margins; as CLIP scores seems to be always in small range.
margin_all = np.array(margin_all)
print(f'mean margin: {margin_all.mean()}')
print(f'std margin: {margin_all.std()}')
dynamic_threshold = margin_all.mean() + 0.5*margin_all.std()
print(f'{dynamic_threshold=}')

generate_html_dashboard(csv_path, html_path)
print("Done. Review images in:", REVIEW_DIR)
print("For bulk delete:   xargs -a meme_candidates.txt rm")
print("Or review files:   xargs -a meme_candidates.txt rm")
