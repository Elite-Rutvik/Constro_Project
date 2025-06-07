document.addEventListener('DOMContentLoaded', function() {
    // State management
    let castings = [];
    let optimizationResults = null; // Store optimization results for export
    let optimizationComplete = false;
    let projectHeight = 2400; // Default height in mm
    
    // DOM Elements
    const inputMethod = document.getElementsByName('input-method');
    const jsonInput = document.getElementById('json-input');
    const manualInput = document.getElementById('manual-input');
    const pdfInput = document.getElementById('pdf-input');
    const jsonFile = document.getElementById('json-file');
    const pdfFile = document.getElementById('pdf-file');
    const uploadBtn = document.getElementById('upload-btn');
    const uploadPdfBtn = document.getElementById('upload-pdf-btn');
    const castingName = document.getElementById('casting-name');
    const shapeName = document.getElementById('shape-name');
    const sideLengths = document.getElementById('side-lengths');
    const addCastingBtn = document.getElementById('add-casting');
    const addShapeBtn = document.getElementById('add-shape');
    const primaryCastingSelect = document.getElementById('primary-casting');
    const runOptimizationBtn = document.getElementById('run-optimization');
    const dataPreview = document.getElementById('data-preview');
    const optimizationResultsDiv = document.getElementById('optimization-results');
    const exportResultsBtn = document.getElementById('export-results');
    const projectHeightInput = document.getElementById('project-height');

    // Add Excel export button (create if doesn't exist)
    let exportExcelBtn = document.getElementById('export-excel');
    if (!exportExcelBtn) {
        exportExcelBtn = document.createElement('button');
        exportExcelBtn.id = 'export-excel';
        exportExcelBtn.textContent = 'Export to Excel';
        exportExcelBtn.className = 'btn btn-secondary';
        exportExcelBtn.style.display = 'none'; // Initially hidden
        exportResultsBtn.parentNode.appendChild(exportExcelBtn);
    }

    // Validation for project height
    projectHeightInput.addEventListener('blur', function() {
        const height = parseFloat(this.value);
        if (isNaN(height) || height <= 0) {
            alert('Please enter a valid positive height value');
            this.value = projectHeight; // Reset to current valid value
        } else {
            projectHeight = height;
        }
    });

    // Initialize project height input
    if (projectHeightInput) {
        projectHeightInput.value = projectHeight;
    }
    
    // Input method toggle
    inputMethod.forEach(input => {
        input.addEventListener('change', function() {
            if (this.value === 'json') {
                jsonInput.classList.remove('hidden');
                manualInput.classList.add('hidden');
                pdfInput.classList.add('hidden');
            } else if (this.value === 'pdf') {
                pdfInput.classList.remove('hidden');
                jsonInput.classList.add('hidden');
                manualInput.classList.add('hidden');
            } else {
                jsonInput.classList.add('hidden');
                pdfInput.classList.add('hidden');
                manualInput.classList.remove('hidden');
            }
        });
    });

    // JSON file upload
    uploadBtn.addEventListener('click', function() {
        if (jsonFile.files.length === 0) {
            alert('Please select a JSON file');
            return;
        }

        const file = jsonFile.files[0];
        const reader = new FileReader();

        reader.onload = function(e) {
            try {
                const data = JSON.parse(e.target.result);
                castings = processJsonData(data);
                updateDataPreview();
                updatePrimaryCastingOptions();
            } catch (error) {
                alert('Error parsing JSON file: ' + error.message);
            }
        };

        reader.readAsText(file);
    });

    // PDF file upload
    uploadPdfBtn.addEventListener('click', function() {
        if (pdfFile.files.length === 0) {
            alert('Please select a PDF file');
            return;
        }

        const file = pdfFile.files[0];
        const formData = new FormData();
        formData.append('pdfFile', file);
        
        // Show loading indicator
        dataPreview.innerHTML = '<div class="loading">Processing PDF... This may take a minute.</div>';
        
        // First, we need to send the PDF to a server endpoint that will extract data
        fetch('/extract-pdf', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("Received data:", data);
            if (!data || Object.keys(data).length === 0) {
                throw new Error('Empty data received from server');
            }
            castings = processJsonData(data);
            updateDataPreview();
            updatePrimaryCastingOptions();
        })
        .catch(error => {
            console.error('PDF processing error:', error);
            dataPreview.innerHTML = `<div class="error-message">Error: ${error.message}</div>`;
            alert('Error processing PDF file. Please try again or use another input method.');
        });
    });

    // Manual input handlers
    addCastingBtn.addEventListener('click', function() {
        const name = castingName.value.trim();
        if (name) {
            const castingNumber = castings.length + 1;
            const formattedName = `casting_${castingNumber}`;
            castings.push({
                name: formattedName,
                shapes: []
            });
            castingName.value = '';
            updateDataPreview();
            updatePrimaryCastingOptions();
        }
    });

    addShapeBtn.addEventListener('click', function() {
        if (castings.length === 0) {
            alert('Please add a casting first');
            return;
        }

        const name = shapeName.value.trim();
        const lengths = sideLengths.value.trim();

        if (name && lengths) {
            try {
                const sides = lengths.split(',').map(x => parseInt(x.trim()));
                const currentCasting = castings[castings.length - 1];
                const shapeNumber = currentCasting.shapes.length + 1;
                const formattedShapeName = `shape_${String.fromCharCode(65 + shapeNumber - 1)}`; // A, B, C, etc.
                
                currentCasting.shapes.push({
                    name: formattedShapeName,
                    sides: sides
                });
                shapeName.value = '';
                sideLengths.value = '';
                updateDataPreview();
            } catch (error) {
                alert('Invalid side lengths. Use comma-separated numbers');
            }
        }
    });

    // Run optimization
    runOptimizationBtn.addEventListener('click', async function() {
        if (castings.length === 0) {
            alert('No castings available');
            return;
        }

        const primaryCasting = primaryCastingSelect.value;
        if (!primaryCasting) {
            alert('Please select a primary casting');
            return;
        }

        try {
            const response = await fetch('/optimize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    castings: castings,
                    primaryCasting: primaryCasting
                })
            });

            const results = await response.json();
            optimizationResults = results; // Store results for export
            optimizationComplete = true;
            displayResults(results);
            
            // Show export buttons
            exportResultsBtn.style.display = 'inline-block';
            exportExcelBtn.style.display = 'inline-block';
        } catch (error) {
            alert('Optimization failed: ' + error.message);
        }
    });

    // Export results to text
    exportResultsBtn.addEventListener('click', function() {
        const results = optimizationResultsDiv.textContent;
        if (!results) {
            alert('No results to export');
            return;
        }

        const blob = new Blob([results], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'optimization_results.txt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });

    // Export results to Excel
    exportExcelBtn.addEventListener('click', function() {
        if (!optimizationComplete || !optimizationResults) {
            alert('Please run optimization first');
            return;
        }

        try {
            // Generate Excel file
            generateExcelFile(optimizationResults);
        } catch (error) {
            alert('Failed to export to Excel: ' + error.message);
        }
    });

    // Clear button handlers
    const clearManualBtn = document.getElementById('clear-manual');
    const clearFileBtn = document.getElementById('clear-file');
    const clearPdfBtn = document.getElementById('clear-pdf');

    if (clearManualBtn) {
        clearManualBtn.addEventListener('click', function() {
            castings = [];
            castingName.value = '';
            shapeName.value = '';
            sideLengths.value = '';
            updateDataPreview();
            updatePrimaryCastingOptions();
            resetExportButtons();
        });
    }

    if (clearFileBtn) {
        clearFileBtn.addEventListener('click', function() {
            castings = [];
            jsonFile.value = '';
            updateDataPreview();
            updatePrimaryCastingOptions();
            resetExportButtons();
        });
    }

    if (clearPdfBtn) {
        clearPdfBtn.addEventListener('click', function() {
            castings = [];
            pdfFile.value = '';
            updateDataPreview();
            updatePrimaryCastingOptions();
            resetExportButtons();
        });
    }

    // Helper functions
    function processJsonData(data) {
        console.log("Raw JSON data:", data);
        try {
            // Create a new array to hold our casting objects
            const processedCastings = [];
            
            // Loop through each casting in the data
            for (const [castingName, castingShapes] of Object.entries(data)) {
                console.log(`Processing casting ${castingName} with shapes:`, castingShapes);
                
                // Create a new casting object with an array for shapes
                const castingObj = {
                    name: castingName,
                    shapes: []
                };
                
                // Loop through each shape in the casting
                for (const [shapeName, shapeData] of Object.entries(castingShapes)) {
                    console.log(`Processing shape ${shapeName} with data:`, shapeData);
                    
                    // Create a shape object with the name and sides array
                    const shapeObj = {
                        name: shapeName,  // This is where the name is assigned
                        sides: []
                    };
                    
                    // Extract side values from the shape data
                    if (shapeData.side_1 !== undefined) {
                        shapeObj.sides.push(shapeData.side_1);
                    }
                    if (shapeData.side_2 !== undefined) {
                        shapeObj.sides.push(shapeData.side_2);
                    }
                    
                    // Add the shape object to the casting's shapes array
                    castingObj.shapes.push(shapeObj);
                }
                
                // Add the casting object to our results array
                processedCastings.push(castingObj);
            }
            
            console.log("Processed castings:", processedCastings);
            return processedCastings;
        } catch (error) {
            console.error("Error processing JSON data:", error);
            throw error;
        }
    }

    function updateDataPreview() {
        try {
            console.log("Updating data preview with castings:", castings);
            
            if (!castings || castings.length === 0) {
                dataPreview.innerHTML = '<pre class="preview-text">No casting data available.</pre>';
                return;
            }
            
            const formattedPreview = castings.map(casting => {
                const shapesData = casting.shapes.map(shape => {
                    // Display the actual shape name (like SW6) directly
                    const shapeName = shape.name;
                    
                    const sidesData = shape.sides.map((length, idx) => 
                        `    Side ${idx + 1}: ${length}`
                    ).join('\n');
                    
                    return `  Shape: ${shapeName}\n${sidesData}`;
                }).join('\n\n');
                
                const castingNumber = casting.name.replace('casting_', '');
                
                return `Casting ${castingNumber}\n${shapesData}`;
            }).join('\n\n');

            dataPreview.innerHTML = `<pre class="preview-text">${formattedPreview}</pre>`;
        } catch (error) {
            console.error("Error updating data preview:", error);
            dataPreview.innerHTML = `<pre class="preview-text error-message">Error displaying data: ${error.message}</pre>`;
        }
    }

    function updatePrimaryCastingOptions() {
        primaryCastingSelect.innerHTML = '<option value="">Select Primary Casting</option>';
        castings.forEach(casting => {
            const option = document.createElement('option');
            option.value = casting.name;
            option.textContent = casting.name;
            primaryCastingSelect.appendChild(option);
        });
    }

    function displayResults(response) {
        const container = document.getElementById('optimization-results');
        container.innerHTML = '';

        try {
            console.log("Displaying results:", response);
            const resultsHtml = `
            <div class="results-content">
                <div class="progress-section">
                    ${response.steps.map(step => `<div class="progress-step">${step}</div>`).join('\n')}
                </div>

                <div class="primary-section">
                    Primary Casting: ${response.results.primary_casting}
                </div>

                <div class="castings-section">
                    ${response.results.castings.map(casting => {
                        const castingNumber = casting.name.includes('_') ? 
                            casting.name.split('_')[1] : 
                            casting.name.replace(/\D/g, '');
                        
                        return `
                        <div class="casting-block ${casting.type.toLowerCase()}">
                            <div class="casting-header">Casting ${castingNumber}</div>
                            <div class="casting-type">${casting.type}</div>
                            ${casting.shapes.map(shape => `
                                <div class="shape-block">
                                    Shape: ${shape.name}
                                    ${shape.sides.map(side => 
                                        `<div class="side-block">
                                            Side ${side.number} (Length: ${side.length}): [${side.panels.join(', ')}]
                                        </div>`
                                    ).join('')}
                                </div>
                            `).join('\n')}
                        </div>`
                    }).join('\n')}
                </div>

                <div class="summary-section">
                    <div class="section-header">PANEL USAGE SUMMARY</div>
                    <div class="stats-block">
                        <div>Total panel types used: ${response.results.panel_stats.totals.total_types}</div>
                        <div>Standard panel types: ${response.results.panel_stats.totals.standard_types}</div>
                        <div>Custom panel types: ${response.results.panel_stats.totals.custom_types}</div>
                    </div>

                    <div class="panel-types">
                        <div class="standard-panels">
                            <div class="type-header">Standard panels:</div>
                            ${Object.entries(response.results.panel_stats.standard)
                                .map(([size, count]) => `
                                    <div class="panel-entry">Size ${size}mm: ${count} panels</div>
                                `).join('')}
                        </div>

                        <div class="custom-panels">
                            <div class="type-header">Custom panels:</div>
                            ${Object.entries(response.results.panel_stats.custom)
                                .map(([size, count]) => `
                                    <div class="panel-entry">Size ${size}mm: ${count} panels</div>
                                `).join('')}
                        </div>
                    </div>
                </div>

                <div class="requirements-section">
                    <div class="section-header">SECONDARY CASTING PANEL REQUIREMENTS</div>
                    <div class="requirements-block">
                        ${response.results.reuse_analysis.new_panels
                            .map(panel => `
                                <div class="requirement-entry ${panel.type}">
                                    Size ${panel.size}mm (${panel.type}): ${panel.count} new panels
                                </div>
                            `).join('')}
                    </div>
                </div>

                <div class="efficiency-section">
                    <div class="totals-block">
                        <div>Total new panels needed: ${response.results.reuse_analysis.totals.total_new}</div>
                        <div>Standard panels: ${response.results.reuse_analysis.totals.standard_new}</div>
                        <div>Custom panels: ${response.results.reuse_analysis.totals.custom_new}</div>
                    </div>

                    <div class="efficiency-block">
                        <div>Panel reuse efficiency: ${response.results.reuse_analysis.efficiency.percentage}%</div>
                        <div>(${response.results.reuse_analysis.efficiency.reused_panels} of 
                        ${response.results.reuse_analysis.efficiency.total_panels} panels reused)</div>
                    </div>
                </div>
            </div>
        `;

            container.innerHTML = resultsHtml;
            container.scrollIntoView({ behavior: 'smooth' });

        } catch (error) {
            console.error('Error displaying results:', error);
            container.innerHTML = `
                <div class="error-message">
                    <h3>Error Processing Results</h3>
                    <p>${error.message}</p>
                </div>
            `;
        }
    }

    function resetExportButtons() {
        optimizationComplete = false;
        optimizationResults = null;
        exportResultsBtn.style.display = 'none';
        exportExcelBtn.style.display = 'none';
        optimizationResultsDiv.innerHTML = '';
    }

    // Area calculation functions
    function calculateColumnPerimeter(sides) {
        // For rectangular columns, perimeter = 2 * (side1 + side2)
        if (sides.length >= 2) {
            return 2 * (sides[0] + sides[1]);
        }
        return 0;
    }

    function calculateShutteringArea(perimeter, height) {
        // Area = perimeter * height (in square meters)
        return (perimeter * height) / 1000000; // Convert from mm² to m²
    }

    function calculateExternalCornerArea(perimeter) {
        // External corner area factor (based on PDF calculation pattern)
        const factor = 1.248; // From PDF analysis
        return (perimeter * factor) / 1000; // Convert to m²
    }

    // Excel generation function - MODIFIED
    function generateExcelFile(results) {
        try {
            // Check if SheetJS library is available
            if (typeof XLSX === 'undefined') {
                // Try to load SheetJS dynamically
                const script = document.createElement('script');
                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js';
                script.onload = function() {
                    generateExcelFile(results);
                };
                script.onerror = function() {
                    throw new Error('Failed to load SheetJS library. Please check your internet connection.');
                };
                document.head.appendChild(script);
                return;
            }

            // Create a new workbook
            const wb = XLSX.utils.book_new();

            // Create Sheet 1: Casting Dimensions & Panel Layouts
            const sheet1Data = createDimensionsSheetData(results);
            const ws1 = XLSX.utils.aoa_to_sheet(sheet1Data);
            
            // Apply styling to sheet 1
            applySheetStyling(ws1, sheet1Data);
            XLSX.utils.book_append_sheet(wb, ws1, "Casting Dimensions & Panels");

            // Create Sheet 2: Panel Summary
            const sheet2Data = createPanelSummarySheetData(results);
            const ws2 = XLSX.utils.aoa_to_sheet(sheet2Data);
            
            // Apply styling to sheet 2
            applySheetStyling(ws2, sheet2Data);
            XLSX.utils.book_append_sheet(wb, ws2, "Panel Summary");

            // Create Sheet 3: Area Calculation with Formulas
            const {data: sheet3Data, formulaCells} = createAreaCalculationSheetDataWithFormulas(results);
            const ws3 = XLSX.utils.aoa_to_sheet(sheet3Data);
            
            // Add formulas to specific cells
            addFormulasToSheet(ws3, formulaCells);
            
            // Apply styling to sheet 3
            applySheetStyling(ws3, sheet3Data);
            XLSX.utils.book_append_sheet(wb, ws3, "Area Calculation");

            // Set column widths for better readability
            setColumnWidths(ws1, [8, 15, 12, 12, 15, 20, 12, 15]);
            setColumnWidths(ws2, [15, 10, 12]);
            setColumnWidths(ws3, [8, 15, 12, 12, 12, 15, 15, 20, 25]);

            // Generate Excel file and download
            const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
            const filename = `optimization_results_${timestamp}.xlsx`;
            
            // Use writeFile with proper options
            XLSX.writeFile(wb, filename, {
                bookType: 'xlsx',
                bookSST: false,
                type: 'binary'
            });

            alert('Excel file has been downloaded successfully!');

        } catch (error) {
            console.error('Excel generation error:', error);
            alert('Excel export failed: ' + error.message + '. Trying CSV export instead...');
            
            // Fallback: Generate CSV files if Excel fails
            generateCSVFiles(results);
        }
    }

    // NEW FUNCTION: Apply styling to sheets
    function applySheetStyling(worksheet, data) {
        if (!worksheet['!cols']) worksheet['!cols'] = [];
        
        // Set header row styling
        const range = XLSX.utils.decode_range(worksheet['!ref']);
        
        for (let R = range.s.r; R <= range.e.r; ++R) {
            for (let C = range.s.c; C <= range.e.c; ++C) {
                const cellAddress = XLSX.utils.encode_cell({r: R, c: C});
                if (!worksheet[cellAddress]) continue;
                
                // Style header rows (first few rows typically contain headers)
                if (R < 5 || (data[R] && data[R][0] && typeof data[R][0] === 'string' && 
                    (data[R][0].includes('Casting') || data[R][0].includes('Summary') || 
                     data[R][0].includes('SHUTTERING') || data[R][0].includes('Sr. No.')))) {
                    
                    if (!worksheet[cellAddress].s) worksheet[cellAddress].s = {};
                    worksheet[cellAddress].s.font = { bold: true };
                    worksheet[cellAddress].s.fill = { fgColor: { rgb: "CCCCCC" } };
                }
            }
        }
    }

    // NEW FUNCTION: Set column widths
    function setColumnWidths(worksheet, widths) {
        if (!worksheet['!cols']) worksheet['!cols'] = [];
        
        widths.forEach((width, index) => {
            worksheet['!cols'][index] = { wch: width };
        });
    }

    // NEW FUNCTION: Add formulas to specific cells
    function addFormulasToSheet(worksheet, formulaCells) {
        formulaCells.forEach(({cell, formula, format}) => {
            if (worksheet[cell]) {
                worksheet[cell].f = formula;
                if (format) {
                    if (!worksheet[cell].s) worksheet[cell].s = {};
                    worksheet[cell].s.numFmt = format;
                }
            }
        });
    }

    // MODIFIED FUNCTION: Create area calculation sheet with formulas
    function createAreaCalculationSheetDataWithFormulas(results) {
        const data = [];
        const formulaCells = [];
        const timestamp = new Date().toLocaleString();
        
        // Add title and project info
        data.push(['SHUTTERING AREA STATEMENT']);
        data.push([`Generated on: ${timestamp}`]);
        data.push([`Project Height: ${projectHeight}mm`]);
        data.push([]); // Empty row

        // Header row
        data.push([
            'Sr. No.',
            'Casting',
            'Shape Name',
            'Column Size S1 (mm)',
            'Column Size S2 (mm)',
            'Column Perimeter (mm)',
            'Column Height (mm)',
            'Column Shuttering Area (Sq.m)',
            'External Corner Area (Sq.m)',
            'Total Area per Set (Sq.m)'
        ]);

        let currentRow = 6; // Starting row for data (after headers)
        let srNo = 1;
        const castingSubtotalRows = [];

        // Process each casting
        results.results.castings.forEach((casting, castingIndex) => {
            const castingStartRow = currentRow;
            
            // Add casting header row
            const castingType = casting.name === results.results.primary_casting ? "PRIMARY" : "SECONDARY";
            data.push([
                '',
                `${casting.name} (${castingType})`,
                '', '', '', '', '', '', '', ''
            ]);
            currentRow++;

            // Process each shape in the casting
            casting.shapes.forEach(shape => {
                if (shape.sides && shape.sides.length >= 2) {
                    const s1 = shape.sides[0].length;
                    const s2 = shape.sides[1].length;
                    
                    // Add data row with placeholders for formulas
                    data.push([
                        srNo,
                        '', // Casting name already shown in header
                        shape.name,
                        s1,
                        s2,
                        '', // Perimeter - will be formula
                        projectHeight,
                        '', // Shuttering area - will be formula
                        '', // External corner area - will be formula
                        ''  // Total area - will be formula
                    ]);

                    // Add formulas for this row
                    const rowLetter = currentRow.toString();
                    
                    // Perimeter formula: 2*(S1+S2)
                    formulaCells.push({
                        cell: `F${rowLetter}`,
                        formula: `2*(D${rowLetter}+E${rowLetter})`,
                        format: '0'
                    });
                    
                    // Shuttering area formula: (Perimeter * Height) / 1000000
                    formulaCells.push({
                        cell: `H${rowLetter}`,
                        formula: `(F${rowLetter}*G${rowLetter})/1000000`,
                        format: '0.00'
                    });
                    
                    // External corner area formula: (Perimeter * 1.248) / 1000
                    formulaCells.push({
                        cell: `I${rowLetter}`,
                        formula: `(0.13*4*G${rowLetter})/1000`,
                        format: '0.00'
                    });
                    
                    // Total area formula: Shuttering area + External corner area
                    formulaCells.push({
                        cell: `J${rowLetter}`,
                        formula: `H${rowLetter}+I${rowLetter}`,
                        format: '0.00'
                    });

                    srNo++;
                    currentRow++;
                }
            });

            // Add casting subtotal row
            const subtotalRow = currentRow;
            data.push([
                '',
                `${casting.name} Subtotal`,
                '', '', '', '', '', '', '',
                '' // Will be sum formula
            ]);
            
            // Add subtotal formula
            const startDataRow = castingStartRow + 2; // Skip casting header
            const endDataRow = currentRow - 1;
            if (endDataRow >= startDataRow) {
                formulaCells.push({
                    cell: `J${subtotalRow}`,
                    formula: `SUM(J${startDataRow}:J${endDataRow})`,
                    format: '0.00'
                });
            }
            
            castingSubtotalRows.push(subtotalRow);
            currentRow++;
            
            // Add empty row between castings
            data.push([]);
            currentRow++;
        });

        // Add grand total
        const grandTotalRow = currentRow;
        data.push([
            '',
            'TOTAL COLUMN SHUTTERING AREA',
            '', '', '', '', '', '', '',
            '' // Will be sum of all subtotals
        ]);
        
        // Add grand total formula
        if (castingSubtotalRows.length > 0) {
            const subtotalReferences = castingSubtotalRows.map(row => `J${row}`).join('+');
            formulaCells.push({
                cell: `J${grandTotalRow}`,
                formula: subtotalReferences,
                format: '0.00'
            });
        }
        
        currentRow++;

        // Add summary information
        data.push([]);
        data.push(['FORMULA EXPLANATIONS']);
        data.push(['Perimeter Formula:', '2 × (Side1 + Side2)']);
        data.push(['Shuttering Area Formula:', '(Perimeter × Height) ÷ 1,000,000']);
        data.push(['External Corner Area Formula:', '(Perimeter × 1.248) ÷ 1,000']);
        data.push(['Total Area Formula:', 'Shuttering Area + External Corner Area']);
        data.push([]);
        data.push(['SUMMARY INFORMATION']);
        data.push(['Total Castings', results.results.castings.length]);
        data.push(['Primary Casting', results.results.primary_casting]);
        data.push(['Project Height (mm)', projectHeight]);

        return { data, formulaCells };
    }

    // MODIFIED FUNCTION: Enhanced dimensions sheet
    function createDimensionsSheetData(results) {
        const data = [];
        const timestamp = new Date().toLocaleString();
        
        // Add title and timestamp
        data.push(['PANEL OPTIMIZATION RESULTS - CASTING DIMENSIONS & PANEL LAYOUTS']);
        data.push([`Generated on: ${timestamp}`]);
        data.push([`Project Height: ${projectHeight}mm`]);
        data.push([]); // Empty row

        // Find primary casting name
        const primaryCasting = results.results.primary_casting;

        // Process each casting
        results.results.castings.forEach(casting => {
            const castingType = casting.name === primaryCasting ? "PRIMARY" : "SECONDARY";
            
            // Casting header
            data.push([`CASTING: ${casting.name} (${castingType})`]);
            
            // Column headers
            data.push(['Shape', 'Side', 'Length (mm)', 'Panel Layout', 'Panel Count', 'Standard Panels', 'Custom Panels']);
            
            // Add shape and side data
            casting.shapes.forEach(shape => {
                shape.sides.forEach((side, sideIdx) => {
                    const panelLayout = side.panels.join(' + ');
                    const panelCount = side.panels.length;
                    
                    // Calculate standard vs custom panels
                    const standardSizes = [100, 200, 300, 400, 500, 600];
                    const standardCount = side.panels.filter(p => standardSizes.includes(p)).length;
                    const customCount = panelCount - standardCount;
                    
                    data.push([
                        sideIdx === 0 ? shape.name : '', // Show shape name only on first side
                        `Side ${side.number}`,
                        side.length,
                        panelLayout,
                        panelCount,
                        standardCount,
                        customCount
                    ]);
                });
            });
            
            // Add empty row between castings
            data.push([]);
        });

        return data;
    }

    // MODIFIED FUNCTION: Enhanced panel summary
    function createPanelSummarySheetData(results) {
        const data = [];
        const timestamp = new Date().toLocaleString();
        
        // Add title and timestamp
        data.push(['PANEL USAGE SUMMARY REPORT']);
        data.push([`Generated on: ${timestamp}`]);
        data.push([`Primary Casting: ${results.results.primary_casting}`]);
        data.push([]); // Empty row

        // Combined Panel Overview
        data.push(['COMPLETE PANEL INVENTORY']);
        data.push(['Panel Size (mm)', 'Standard Count', 'Custom Count', 'Total Count']);
        
        // Get all unique panel sizes
        const allSizes = new Set([
            ...Object.keys(results.results.panel_stats.standard),
            ...Object.keys(results.results.panel_stats.custom)
        ]);
        
        const totalAllPanels = Object.values(results.results.panel_stats.standard).reduce((a, b) => a + b, 0) +
                               Object.values(results.results.panel_stats.custom).reduce((a, b) => a + b, 0);
        
        Array.from(allSizes)
            .map(size => parseInt(size))
            .sort((a, b) => a - b)
            .forEach(size => {
                const sizeStr = size.toString();
                const standardCount = results.results.panel_stats.standard[sizeStr] || 0;
                const customCount = results.results.panel_stats.custom[sizeStr] || 0;
                const totalCount = standardCount + customCount;
                
                data.push([
                    `${size}mm`,
                    standardCount,
                    customCount,
                    totalCount
                ]);
            });
        
        data.push([]); // Empty row

        // Summary Statistics
        data.push(['SUMMARY STATISTICS']);
        data.push(['Metric', 'Value', 'Percentage']);
        
        const totalStandard = Object.values(results.results.panel_stats.standard).reduce((a, b) => a + b, 0);
        const totalCustom = Object.values(results.results.panel_stats.custom).reduce((a, b) => a + b, 0);
        const totalPanels = totalStandard + totalCustom;
        
        data.push(['Total Panels Used', totalPanels, '100.0%']);
        data.push(['Standard Panels', totalStandard, totalPanels > 0 ? `${(totalStandard/totalPanels*100).toFixed(1)}%` : '0.0%']);
        data.push(['Custom Panels', totalCustom, totalPanels > 0 ? `${(totalCustom/totalPanels*100).toFixed(1)}%` : '0.0%']);
        data.push(['Standard Panel Types', Object.keys(results.results.panel_stats.standard).length, '']);
        data.push(['Custom Panel Types', Object.keys(results.results.panel_stats.custom).length, '']);
        data.push(['Total Panel Types', results.results.panel_stats.totals.total_types, '']);
        
        data.push([]); // Empty row

        // Efficiency Analysis
        data.push(['EFFICIENCY ANALYSIS']);
        data.push(['Panel Reuse Efficiency', `${results.results.reuse_analysis.efficiency.percentage}%`]);
        data.push(['Panels Reused', results.results.reuse_analysis.efficiency.reused_panels]);
        data.push(['Total Panels in Analysis', results.results.reuse_analysis.efficiency.total_panels]);
        data.push(['New Panels Required', results.results.reuse_analysis.totals.total_new]);

        return data;
    }

    // Fallback function to generate CSV files if Excel export fails
    function generateCSVFiles(results) {
        try {
            // Generate dimensions CSV
            const dimensionsData = createDimensionsSheetData(results);
            const dimensionsCSV = convertArrayToCSV(dimensionsData);
            downloadCSV(dimensionsCSV, 'casting_dimensions_panels.csv');

            // Generate summary CSV
            const summaryData = createPanelSummarySheetData(results);
            const summaryCSV = convertArrayToCSV(summaryData);
            downloadCSV(summaryCSV, 'panel_summary.csv');

            // Generate area calculation CSV
            const areaData = createAreaCalculationSheetData(results);
            const areaCSV = convertArrayToCSV(areaData);
            downloadCSV(areaCSV, 'area_calculation.csv');

            alert('Excel export failed, but CSV files have been generated successfully.');
        } catch (error) {
            console.error('CSV generation error:', error);
            throw new Error('Both Excel and CSV export failed');
        }
    }

    function convertArrayToCSV(data) {
        return data.map(row => 
            row.map(cell => {
                // Handle cells that might contain commas or quotes
                if (typeof cell === 'string' && (cell.includes(',') || cell.includes('"'))) {
                    return `"${cell.replace(/"/g, '""')}"`;
                }
                return cell || '';
            }).join(',')
        ).join('\n');
    }

    function downloadCSV(csvString, filename) {
        const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
});