import React, { useState } from 'react';
import { AsyncTypeahead } from 'react-bootstrap-typeahead';
import Form from 'react-bootstrap/Form';

const SnomedSearch = (args) => {

  const [isLoading, setIsLoading] = useState(false);
  const [options, setOptions] = useState([]);
  const [code, setCode] = useState([]);
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
    if (selected.length === 1) {
      setincludedCodeCount("");
      fetch(`/api/snomed/count-descendants-and-self?code=${selected[0].code}`)
          .then(response => response.json())
          .then(data => {
            setincludedCodeCount(data.expansion.total || "");
          });
    }
  };

  return (
  <div>
    <Form.Group className="mb-3">
      <Form.Label>{args.label}</Form.Label>
      <Form.Check type="radio" id="must_have_{label}" label="Must have" checked={true} />
      <Form.Check type="radio" id="must_have_{label}" label="Must not have" checked={false} />
      <AsyncTypeahead
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
