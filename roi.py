import cv2
import json

# Initialize variables
drawing = False
start_point = (0, 0)
roi_coords = {}  # Store ROI coordinates
current_label = None  # Current ROI label being edited
temp_image = None  # Temporary image for drawing rectangles
output_path = r"C:\Users\HARSH\stamp_paper_ocr\updated_rois.json"  # Save coordinates
plot_path = r"C:\Users\HARSH\stamp_paper_ocr\roi_plot.png"  # Save plotted image

# Instructions
print("""
Instructions:
1. Press 'n' to move to the next ROI label.
2. Press 's' to save the coordinates and plotted image.
3. Press 'q' to quit.
4. Use the left mouse button to draw the rectangle.
""")

# Predefined ROI labels (you can modify these as needed)
roi_labels = ["certificate_number", "reference_number", "denomination", "state"]
label_index = 0

# Load the image
image_path = r"C:\Users\HARSH\Downloads\stamp papers1_page-0006.jpg"
image = cv2.imread(image_path)
if image is None:
    raise ValueError("Image could not be loaded. Check the file path.")

# Resize for easier viewing (optional)
image = cv2.resize(image, (800, 800))
temp_image = image.copy()

# Get image dimensions
height, width = image.shape[:2]

def draw_rectangle(event, x, y, flags, param):
    """Callback function for drawing rectangles with the mouse."""
    global drawing, start_point, temp_image, roi_coords, current_label

    if event == cv2.EVENT_LBUTTONDOWN:
        # Start drawing
        drawing = True
        start_point = (x, y)

    elif event == cv2.EVENT_MOUSEMOVE:
        # Update rectangle while dragging
        if drawing:
            temp_image = image.copy()
            cv2.rectangle(temp_image, start_point, (x, y), (0, 255, 0), 2)

    elif event == cv2.EVENT_LBUTTONUP:
        # Finish drawing
        drawing = False
        end_point = (x, y)
        if current_label:
            # Normalize coordinates and save
            x1, y1 = min(start_point[0], end_point[0]), min(start_point[1], end_point[1])
            x2, y2 = max(start_point[0], end_point[0]), max(start_point[1], end_point[1])
            roi_coords[current_label] = (
                (x1 / width, y1 / height), (x2 / width, y2 / height)
            )
            print(f"ROI for {current_label} updated: {roi_coords[current_label]}")
        temp_image = image.copy()

# Set up OpenCV window and mouse callback
cv2.namedWindow("ROI Editor")
cv2.setMouseCallback("ROI Editor", draw_rectangle)

while True:
    # Show the image
    cv2.imshow("ROI Editor", temp_image)
    key = cv2.waitKey(1) & 0xFF

    if key == ord('n'):  # Move to the next ROI
        if label_index < len(roi_labels):
            current_label = roi_labels[label_index]
            label_index += 1
            print(f"Editing ROI for: {current_label}")
        else:
            print("No more ROIs to edit.")
    elif key == ord('s'):  # Save ROIs and plot
        # Save ROIs to a JSON file
        with open(output_path, "w") as file:
            json.dump(roi_coords, file, indent=4)
        print(f"Updated ROIs saved to {output_path}")

        # Save the plotted image
        for label, ((x1_ratio, y1_ratio), (x2_ratio, y2_ratio)) in roi_coords.items():
            x1, y1 = int(x1_ratio * width), int(y1_ratio * height)
            x2, y2 = int(x2_ratio * width), int(y2_ratio * height)
            cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(image, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.imwrite(plot_path, image)
        print(f"Plotted image with ROIs saved to {plot_path}")
    elif key == ord('q'):  # Quit the editor
        print("Exiting ROI Editor.")
        break

cv2.destroyAllWindows()
