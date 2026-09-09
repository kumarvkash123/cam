# Document Upload Loader V28

Added an explicit busy/loading state to the borrower Documents Center.

- Loader starts immediately after **Upload & Process Documents** is clicked.
- Shows OCR / classification / extraction processing message.
- Upload button changes to a spinner + **Processing Documents...**.
- Browse input and upload button are disabled while the request is running to prevent duplicate uploads.
- Loader is cleared in a `finally` block on both success and failure.
- Existing processed-document results remain visible while new documents are processed.
