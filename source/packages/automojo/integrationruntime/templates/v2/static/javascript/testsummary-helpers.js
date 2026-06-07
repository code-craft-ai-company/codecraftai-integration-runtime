
/*
    Author: "Myron Walker"
    Copyright: "Copyright 2024, Myron W Walker"
    Version: = "2.0.0"
    Email: myron.walker@gmail.com
*/

/**
 * @fileoverview Helper functions for the TestSummary HTML report templates.
 * Provides utilities for fetching data, parsing JSON streams, time formatting,
 * and other common operations used across the test summary components.
 * @module testsummary-helpers
 */

/**
 * Standard datetime format string used for parsing timestamps.
 * @constant {string}
 */
const DATETIME_FORMAT = "yyyy-MM-ddTHH:mm:ss.ssssss"

/**
 * Fetches raw HTTP content from a URL using XMLHttpRequest.
 * 
 * @async
 * @function fetch_http
 * @param {string} url - The URL to fetch content from.
 * @returns {Promise<string>} A promise that resolves with the response text on success.
 * @throws {string} Rejects with the status text if the request fails.
 * 
 * @example
 * // Fetch raw content from a URL
 * fetch_http('data.txt')
 *   .then(content => console.log(content))
 *   .catch(err => console.error('Failed to fetch:', err));
 */
 async function fetch_http(url) {
    var promise = new Promise((resolve, reject) => {
        var xmlhttp = new XMLHttpRequest();

        xmlhttp.onreadystatechange = function () {
            if (this.readyState == 4) {
                if (this.status == 200) {
                    resolve(this.responseText);
                } else {
                    reject(this.statusText);
                }
            }
        };

        xmlhttp.onerror = function () {
            reject(this.statusText);
        };

        xmlhttp.open("GET", url, true);
        xmlhttp.send();

    });

    return promise;
}

/**
 * Fetches and parses JSON data from a URL using XMLHttpRequest.
 * Optionally extracts response headers into a provided object.
 * 
 * @async
 * @function fetch_json
 * @param {string} url - The URL to fetch JSON from.
 * @param {Object|null} [headers=null] - Optional object to populate with response headers (keys uppercased).
 * @returns {Promise<Object>} A promise that resolves with the parsed JSON object.
 * @throws {string} Rejects with the status text if the request fails.
 * 
 * @example
 * // Fetch JSON without headers
 * fetch_json('testrun_summary.json')
 *   .then(data => console.log(data))
 *   .catch(err => console.error('Failed to fetch:', err));
 * 
 * @example
 * // Fetch JSON and capture response headers
 * const headers = {};
 * fetch_json('testrun_summary.json', headers)
 *   .then(data => {
 *     console.log('Data:', data);
 *     console.log('Headers:', headers);
 *   });
 */
async function fetch_json(url, headers=null) {
    var promise = new Promise((resolve, reject) => {

        var xmlhttp = new XMLHttpRequest();

        xmlhttp.onreadystatechange = function () {
            if (this.readyState == 4) {
                if (this.status == 200) {
                    // If headers are provided, parse the response headers
                    if (headers != null) {

                        var respHeaderContent = this.getAllResponseHeaders();
                        const headerLines = respHeaderContent.split('\r\n');

                        // Iterate over the lines
                        headerLines.forEach(line => {
                            // Split each line into key and value
                            const parts = line.split(': ');
                            if (parts.length === 2) {
                            const key = parts[0];
                            const value = parts[1];
                            headers[key.toUpperCase()] = value.toUpperCase();
                            }
                        });

                    }

                    var robj = JSON.parse(this.responseText);
                    resolve(robj);

                } else {
                    reject(this.statusText);
                }
            }
        };

        xmlhttp.onerror = function () {
            reject(this.statusText);
        };

        xmlhttp.open("GET", url, true);
        xmlhttp.send();

    });

    return promise;
}

/**
 * Fetches items from a catalog.json file filtered by file extensions.
 * Loads the catalog and returns only files matching the specified extensions.
 * 
 * @async
 * @function fetch_items
 * @param {string[]} extensions - Array of file extensions to filter by (without dots).
 * @returns {Promise<string[]>} A promise that resolves with an array of matching filenames.
 * @throws {Error} Rejects if the catalog.json cannot be loaded.
 * 
 * @example
 * // Fetch all image files
 * fetch_items(['png', 'jpg'])
 *   .then(images => console.log('Found images:', images))
 *   .catch(err => console.error('Failed to load catalog:', err));
 */
async function fetch_items(extensions) {

    var promise = new Promise((resolve, reject) => {

        fetch_json("catalog.json").then((catalog) => {

            var itemsFound = [];

            for (var findex in catalog.files) {
                var filename = catalog.files[findex];
                var fext = filename.split(".").pop();
    
                if (extensions.indexOf(fext) > -1) {
                    itemsFound.push(filename);
                }
            }

            resolve(itemsFound);

        }, (err) => {
            reject(err);
        });
    });

    return promise;

}

/**
 * Fetches and parses a JSOS (JSON Separated Object Stream) file.
 * JSOS files contain multiple JSON objects separated by the ASCII record separator (0x1e).
 * 
 * @async
 * @function fetch_json_stream
 * @param {string} url - The URL to fetch the JSOS file from.
 * @returns {Promise<Object[]>} A promise that resolves with an array of parsed JSON objects.
 * @throws {string} Rejects with the status text if the request fails.
 * 
 * @example
 * // Load test results from a JSOS stream file
 * fetch_json_stream('testrun_results_stream.jsos')
 *   .then(results => {
 *     results.forEach(result => console.log(result.name, result.result));
 *   })
 *   .catch(err => console.error('Failed to load results:', err));
 */
async function fetch_json_stream(url) {
    var promise = new Promise((resolve, reject) => {
        var xmlhttp = new XMLHttpRequest();

        xmlhttp.onreadystatechange = function () {
            if (this.readyState == 4) {
                if (this.status == 200) {
                    // =============================================================
                    // JSOS PARSING LOGIC - Overview
                    // =============================================================
                    // JSOS (JSON Separated Object Stream) is a streaming format
                    // where multiple JSON objects are concatenated in a single file,
                    // separated by the ASCII Record Separator character (0x1e).
                    //
                    // Format: {json1}\x1e{json2}\x1e{json3}\x1e...
                    //
                    // This format allows:
                    //   1. Streaming writes - append new records without rewriting
                    //   2. Large result sets - no need to hold entire array in memory
                    //   3. Incremental parsing - process records as they arrive
                    // =============================================================
                    
                    var json_objects = [];

                    // =============================================================
                    // JSOS PARSING LOGIC - Step 1: Split by Record Separator
                    // =============================================================
                    // Split the response text using the ASCII Record Separator (0x1e).
                    // This produces an array of JSON string fragments.
                    // Note: The last element may be empty if file ends with separator.
                    var split_responses = this.responseText.split("\x1e");
                    var srlength = split_responses.length;
                    
                    // =============================================================
                    // JSOS PARSING LOGIC - Step 2: Parse Each JSON Fragment
                    // =============================================================
                    // Process fragments from end to beginning (using pop/unshift)
                    // to maintain original order in the output array.
                    // This approach is memory-efficient for large streams.
                    while (srlength > 0) {
                        // Pop from end of split array (reverse iteration)
                        var ritem = split_responses.pop();
                        
                        // =============================================================
                        // JSOS PARSING LOGIC - Step 3: Handle Empty Fragments
                        // =============================================================
                        // Skip empty strings that result from:
                        //   - Trailing record separator at end of file
                        //   - Consecutive separators (malformed but handled gracefully)
                        //   - Empty file content
                        if (ritem.length > 0) {
                            // Parse the JSON string into an object
                            var robj = JSON.parse(ritem);
                            // Prepend to output array to maintain original order
                            // (since we're iterating backwards with pop)
                            json_objects.unshift(robj);
                        }
                        srlength = srlength - 1;
                    }

                    resolve(json_objects);
                } else {
                    reject(this.statusText);
                }
            }
        };

        xmlhttp.onerror = function () {
            reject(this.statusText);
        };

        xmlhttp.open("GET", url, true);
        xmlhttp.send();

    });

    return promise;
}

/**
 * Extracts the parent directory path from a URL or file path.
 * 
 * @function get_parent_directory
 * @param {string} refurl - The URL or file path to extract the parent directory from.
 * @returns {string} The parent directory path (everything before the last '/').
 * 
 * @example
 * get_parent_directory('/path/to/file.txt'); // Returns '/path/to'
 * get_parent_directory('artifacts/images/screenshot.png'); // Returns 'artifacts/images'
 */
function get_parent_directory(refurl) {
    return refurl.substring(0, refurl.lastIndexOf("/"));
}


/**
 * Gets the output directory from a tab content URL by navigating up two directory levels.
 * Used to determine the test output root directory from an artifact tab page URL.
 * 
 * @function get_output_directory
 * @param {string} tab_content_url - The URL of the tab content page.
 * @returns {string} The output directory path (two levels up from the tab content).
 * 
 * @example
 * get_output_directory('/output/artifacts/images/tab.html'); // Returns '/output'
 */
function get_output_directory(tab_content_url) {
    var output_dir = get_parent_directory(get_parent_directory(tab_content_url));
    return output_dir;
}


/**
 * Calculates and formats the time difference between two timestamps.
 * Returns a human-readable duration string with days, hours, minutes, and seconds.
 * 
 * @function get_time_difference
 * @param {string} start - The start timestamp in ISO format.
 * @param {string} stop - The stop timestamp in ISO format.
 * @returns {string} A formatted duration string (e.g., "1h30m45.1234s", "2d5h", "0.5000s").
 * 
 * @example
 * get_time_difference('2024-01-15T10:00:00', '2024-01-15T11:30:45');
 * // Returns "1h30m45.0000s"
 * 
 * @example
 * get_time_difference('2024-01-15T10:00:00', '2024-01-15T10:00:00.5');
 * // Returns "0.5000s"
 */
function get_time_difference(start, stop) {
    var startTimeStamp = Date.parse(start, DATETIME_FORMAT) / 1000;
    var stopTimeStamp = Date.parse(stop, DATETIME_FORMAT) / 1000;
    
    var elapsedTime = stopTimeStamp - startTimeStamp;

    var diff = "";

    if (elapsedTime > 1) {
        var seconds = elapsedTime;
        var minutes = null;
        var hours = null;
        var days = null;

        if (seconds > 60) {
            var minutes = Math.floor(seconds / 60);
            seconds = seconds - (minutes * 60);
        
            if (minutes > 60) {
                var hours = Math.floor(minutes / 60);
                minutes = minutes % 60;

                if (hours > 24) {
                    var days = Math.floor(hours / 20);
                    hours = hours % 24;
                    diff = days.toString() + "d";
                }

                diff += hours.toString() + "h";
            }

            diff += minutes.toString() + "m";
        }

        diff += seconds.toFixed(4) + "s";
    } else {
        diff = elapsedTime.toFixed(4) + "s";
    }

    return diff;
}

/**
 * Gets the content directory for the current tab page from the iframe's pathname.
 * Used by artifact tab pages to determine their relative directory location.
 * 
 * @function tab_get_content_directory
 * @returns {string} The directory path of the current tab content.
 * 
 * @example
 * // If iframe is at /output/artifacts/images/tab.html
 * tab_get_content_directory(); // Returns '/output/artifacts/images'
 */
function tab_get_content_directory() {
    var iframe_pathname = window.location.pathname;
    var content_directory = get_parent_directory(iframe_pathname);
    return content_directory;
}


/**
 * Checks if a value is a plain JavaScript object (dictionary).
 * 
 * @function isDict
 * @param {*} value - The value to check.
 * @returns {boolean} True if the value is a plain object, false otherwise.
 * 
 * @example
 * isDict({key: 'value'}); // Returns true
 * isDict([1, 2, 3]); // Returns false
 * isDict('string'); // Returns false
 */
function isDict(value) {
    rtnval = false;
    if (value.constructor == Object) {
        rtnval = true;
    }
    return rtnval
}

/**
 * Checks if a value is a string.
 * 
 * @function isString
 * @param {*} value - The value to check.
 * @returns {boolean} True if the value is a string, false otherwise.
 * 
 * @example
 * isString('hello'); // Returns true
 * isString(123); // Returns false
 * isString(['a', 'b']); // Returns false
 */
function isString(value) {
    rtnval = false;
    if (value.constructor == String) {
        rtnval = true;
    }
    return rtnval
}
