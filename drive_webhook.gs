/**
 * Google Drive Webhook for the Job Scraper MCP Server (Option A — no GCP setup).
 *
 * Deploy once, paste the Web App URL into .env as GOOGLE_DRIVE_WEBHOOK_URL.
 *
 * Setup (2 minutes):
 *   1. Open https://script.google.com → New project.
 *   2. Replace the default Code.gs content with this file.
 *   3. Deploy → New deployment → type "Web app":
 *        - Execute as: Me
 *        - Who has access: Anyone
 *   4. Copy the deployment URL (https://script.google.com/macros/s/.../exec).
 *   5. Paste it into .env: GOOGLE_DRIVE_WEBHOOK_URL="https://script.google.com/macros/s/.../exec"
 *
 * The server POSTs { file_name, folder, content } for each mode run; this
 * script writes it as a JSON file into your Drive folder (created if missing)
 * and returns the Drive link so Gemini Spark can ingest the full dataset
 * without megabyte-scale MCP responses.
 */
function doPost(e) {
  try {
    var body = JSON.parse(e.postData.contents);
    var folderName = body.folder || "gemini spark data";
    var fileName = body.file_name || "mode1.json";

    var folders = DriveApp.getFoldersByName(folderName);
    var folder = folders.hasNext() ? folders.next() : DriveApp.createFolder(folderName);

    var existingFiles = folder.getFilesByName(fileName);
    var file;

    if (existingFiles.hasNext()) {
      file = existingFiles.next();
      file.setContent(body.content);
      while (existingFiles.hasNext()) {
        existingFiles.next().setTrashed(true);
      }
    } else {
      var blob = Utilities.newBlob(body.content, "application/json", fileName);
      file = folder.createFile(blob);
    }

    return ContentService
      .createTextOutput(JSON.stringify({
        status: "success",
        file_name: fileName,
        file_id: file.getId(),
        drive_link: file.getUrl()
      }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({
        status: "error",
        message: String(err)
      }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
