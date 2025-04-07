import React, { useState } from 'react';
import { AsyncTypeahead } from 'react-bootstrap-typeahead';
import Form from 'react-bootstrap/Form';

const SnomedSearch = (args) => {

  const [code, setCode] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [options, setOptions] = useState([]);
  const [includedCodeCount, setincludedCodeCount] = useState("");

  const handleSearch = (query) => {
    setIsLoading(true);
    setincludedCodeCount("");
    // Replace with actual API call
    fetch(`/api/snomed/search?ecl=<<${args.target_code}&term=${query}`)
      .then(response => response.json())
      .then(data => {
        setOptions(data.expansion.contains || []);
        setIsLoading(false);
      });
  };

  const selectCode = (selected) => {
    setCode(selected);
    if (args.onSelect) {
      args.onSelect({
          code: selected,
      });
    }
    if (selected.length === 1) {
      setincludedCodeCount("");
      fetch(`/api/snomed/count-descendants-and-self?code=${selected[0].code}`)
          .then(response => response.json())
          .then(data => {
            setincludedCodeCount(data.expansion.total || "");
          });
      console.log(getSelection())
    }
  };

  return (
    <div>
      <Form.Group className="mb-3">
        <Form.Label>{args.label}</Form.Label>
        <p><i>Start typing to search and add SNOMED terms. Click ? to remove.</i></p>
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
        <p><i>{(includedCodeCount !== "") &&<span>Includes {includedCodeCount} code</span>}{(includedCodeCount > 1) && <span>s</span>}</i></p>
      </Form.Group>
    </div>
  );
};

export default SnomedSearch;
