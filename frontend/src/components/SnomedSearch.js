import React, { useState } from 'react';
import { AsyncTypeahead } from 'react-bootstrap-typeahead';
import Form from 'react-bootstrap/Form';

const SnomedSearch = (args) => {
  const [code, setCode] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [options, setOptions] = useState([]);

  const handleSearch = (query) => {
    setIsLoading(true);
    fetch(`/api/snomed/search?ecl=<<${args.target_code}&term=${query}`)
      .then(response => response.json())
      .then(data => {
        setOptions(data.expansion.contains || []);
        setIsLoading(false);
      });
  };

  const selectCode = (selected) => {
    setCode(selected);
    if (selected.length === 1) {
      const selectedItem = selected[0];
      fetch(`/api/snomed/count-descendants-and-self?code=${selectedItem.code}`)
          .then(response => response.json())
          .then(data => {
            // Log the entire API response to check the structure
            // console.log("API Response:", data);
        
            // Extract the count from the data
            const count = data.expansion.total || 0;
        
            // Log the count value
            // console.log("Total count:", count);
        
            // Extract the array of codes, display values, and their counts
            const codesWithDetails = data.expansion.contains.map(item => ({
              code: item.code,
              display: item.display,
              count: count,  // You can set it to the same count if it's meant to be the same for all
            }));
        
            // Log the array of codes, displays, and counts
            // console.log("Codes with details:", codesWithDetails);
        
            // Pass the extracted data to onSelect if provided
            if (args.onSelect) {
              args.onSelect({
                code: selected,
                display: selectedItem.display,
                count: count,
                codesWithDetails: codesWithDetails, // Pass all the details in an array
              });
            }
          })
          .catch(error => {
            console.error("Error fetching child codes:", error);
          });
    }
  };

  return (
    <div>
      <Form.Group className="mb-3">
        <Form.Label>{args.label}</Form.Label>
        <p><i>Start typing to search and add SNOMED terms. Click × to remove.</i></p>
        <AsyncTypeahead
          id={args.label}
          labelKey="display"
          options={options}
          isLoading={isLoading}
          onSearch={handleSearch}
          placeholder="Search for something..."
          selected={code}
          onChange={selectCode}
        />
      </Form.Group>
    </div>
  );
};

export default SnomedSearch;
