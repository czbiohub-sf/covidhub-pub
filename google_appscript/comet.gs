function onFormSubmit(e) {
  let formName = "";
  let formValues = {};
  if (e) {
    formValues = e.namedValues;
    formName = e.range.getSheet().getName();
    console.log("Submitted: ", formName);
    console.log(formValues);
  }

  const botConfig = SpreadsheetApp.getActive()
      .getSheetByName("Bot Config")
      .getDataRange()
      .getValues();

  const postToLambda = requestData => {
    const endpoint = botConfig[0][1];
    const apiKey = botConfig[0][2];
    const options = {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(requestData),
      headers: {
        "x-api-key": apiKey,
      },
    };
    UrlFetchApp.fetch(endpoint, options);
  };

  const postToStagingLambda = requestData => {
    const staging_endpoint = botConfig[1][1];
    const staging_apiKey = botConfig[1][2];

    const staging_options = {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(requestData),
      headers: {
        "x-api-key": staging_apiKey
      }
    };
    UrlFetchApp.fetch(staging_endpoint, staging_options);
  };

  const postToSlack = (channel, text) => {
    const requestData = { channel: channel, text: text };
    const options = {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(requestData),
    };
    const slackHook = botConfig[0][0];
    UrlFetchApp.fetch(slackHook, options);
  };

  const formatAndSubmit = (actionName, params = []) => {
    const requestData = { action: actionName };
    for (const p of params) {
      requestData[p] = formValues[p].find(x => x.length);
    }
    // Sleep to give the files longer to upload.
    Utilities.sleep(2000);
    postToLambda(requestData);
    Utilities.sleep(2000);
    postToStagingLambda(requestData);
  };

  if (formName === "External Samples Shipment Metadata") {
    const params = [
      "Please upload the CZB metadata form",
      "Project",
      "Samples received date",
    ];
    formatAndSubmit("external_sample_shipment", params);
  } else if (formName === "Comet New Sample Arrival") {
    const params = [
      "OG plate barcode",
      "Please upload the metadata (.xlsx file) associated with the OG plate"
    ];
    formatAndSubmit("sample_database", params);
  } else if (formName === "COMET Input Plate") {
    const params = [
      "96 COMET Sample ID file",
      "96 COMET Plate Barcode",
      "96 COMET Destination Plate Barcode",
      "96 COMET Source Plate File (OG or RX)",
      "What would you like to do?",
      "96 COMET Sample Accessions file",
      "96 COMET Sample Accessions file (full 96 wells)"
    ];
    // Sleep to give the files longer to upload.
    Utilities.sleep(15000);
    formatAndSubmit("draw_96_plate_map", params);
  } else if (formName === "Combine 96 into 384") {
    const params = [
      "384 COMET Sequencing Plate Name",
      "96 COMET Sample Plate 1 Barcode",
      "96 COMET Sample Plate 2 Barcode",
      "96 COMET Sample Plate 3 Barcode",
      "96 COMET Sample Plate 4 Barcode",
      "Are you concatenating inner 60 or 96 plates?",
    ];
    formatAndSubmit("concat_96_384", params);
  } else if (formName === "COMET Index Plates") {
    const params = [
      "COMET 384 Index Plate Name",
      "COMET 384 Index Plate",
      "COMET 384 Sequencing Plate Barcode",
    ];
    formatAndSubmit("bind_index_plate", params);
  } else if (formName === "COMET sequencing form") {
    const values = e.namedValues;
    const j = "COMET 384 Sequencing Plate";
    const k = "COMET Run ID";
    const filteredData = { [j]: values[j], [k]: values[k] };
    const sortedKeys = Object.keys(filteredData).sort();
    let output = "\n";
    for (const key of sortedKeys) {
      output += `*${key}*: ${filteredData[key]}\n`;
    }
    postToSlack("#covid_mngs", `*Form "${formName}" submitted:*\n${output}`);
    postToSlack(
      "#covid19ngs_analysis",
      `*Form "${formName}" submitted:*\n${output}`
    );
  } else if (formName === "COMET Lookups") {
    const params = [
      "Please input a list of accessions",
      "Alternatively, please upload an Excel file with the accessions or CZB_IDs you'd like to lookup",
    ];
    formatAndSubmit("metadata_lookup", params);
  } else if (formName === "COMET Cherry Picking Trigger") {
    const params = [
      "If there are any new locations under the IRB, please add them here separated by commas"
    ];
    formatAndSubmit("update_ripe_samples", params);
  }
}
