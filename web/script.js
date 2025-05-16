document.addEventListener('DOMContentLoaded', function() {
    // State management
    let castings = [];
    
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
    const optimizationResults = document.getElementById('optimization-results');
    const exportResultsBtn = document.getElementById('export-results');

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
            displayResults(results);
        } catch (error) {
            alert('Optimization failed: ' + error.message);
        }
    });

    // Export results
    exportResultsBtn.addEventListener('click', function() {
        const results = optimizationResults.textContent;
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

    // Add these new functions after the existing event listeners
    const clearManualBtn = document.getElementById('clear-manual');
    const clearFileBtn = document.getElementById('clear-file');
    const clearPdfBtn = document.getElementById('clear-pdf');

    // Clear manual input
    clearManualBtn.addEventListener('click', function() {
        castings = [];
        castingName.value = '';
        shapeName.value = '';
        sideLengths.value = '';
        updateDataPreview();
        updatePrimaryCastingOptions();
    });

    // Clear file input
    clearFileBtn.addEventListener('click', function() {
        castings = [];
        jsonFile.value = '';
        updateDataPreview();
        updatePrimaryCastingOptions();
    });

    // Clear PDF input
    clearPdfBtn.addEventListener('click', function() {
        castings = [];
        pdfFile.value = '';
        updateDataPreview();
        updatePrimaryCastingOptions();
    });
});
