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
          const count = data.expansion.total || 0;
          if (args.onSelect) {
            args.onSelect({
              code: selected,
              display: selectedItem.display,
              count: count
            });
          }
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
