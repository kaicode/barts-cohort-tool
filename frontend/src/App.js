import './App.css';
import React, { useState, useEffect } from 'react';
import { Button, Form } from "react-bootstrap";
import SnomedSearch from "./components/SnomedSearch";

import { ethnicityOptions, genderOptions, defaultAgeRange } from './config/formOptions';

function App() {
  useEffect(() => {
    document.title = "Patient Cohorting Tool";
  }, []);

  const [title, setTitle] = useState("");
  const [selectedGenders, setSelectedGenders] = useState([]);
  const [minAge, setMinAge] = useState(defaultAgeRange.min);
  const [maxAge, setMaxAge] = useState(defaultAgeRange.max);
  const [ethnicity, setEthnicity] = useState([]);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [mustHaveFindings, setMustHaveFindings] = useState([]);
  const [mustNotHaveFindings, setMustNotHaveFindings] = useState([]);
  const [includeChildCodesHave, setIncludeChildCodesHave] = useState(true);
  const [includeChildCodesNotHave, setIncludeChildCodesNotHave] = useState(true);

  const handleEthnicityChange = (code, label) => {
    setEthnicity((prev) => {
      const ethnicityItem = { code, display: label };
      return prev.some(item => item.code === code)
        ? prev.filter(item => item.code !== code)
        : [...prev, ethnicityItem];
    });
  };

  const handleGenderChange = (code, label) => {
    setSelectedGenders((prev) => {
      const genderItem = { code, display: label };
      return prev.some(item => item.code === code)
        ? prev.filter(item => item.code !== code)
        : [...prev, genderItem];
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    const formatFindings = (items) =>
      items.map(item => ({
        code: item.code,
        codesWithDetails: includeChildCodesHave
          ? item.codesWithDetails
          : [item.codesWithDetails.find(d => d.code === item.code[0].code)],
        display: item.display,
        count: includeChildCodesHave
          ? item.count
          : 1
      }));

    const cohortDefinition = {
      title,
      gender: selectedGenders.length === 0 ? "ALL" : selectedGenders,
      ageRange: { min: minAge, max: maxAge },
      ethnicity: ethnicity.length === 0 ? "ALL" : ethnicity,
      timeRange: {
        ...(startDate && { start: startDate }),
        ...(endDate && { end: endDate }),
      },
      mustHaveFindings: mustHaveFindings.map(item => ({
        code: item.code,
        codesWithDetails: includeChildCodesHave ? item.codesWithDetails : [item.codesWithDetails.find(code => code.code === item.code[0].code)],
        display: item.display,
        count: includeChildCodesHave ? item.count : 1
      })),
      mustNotHaveFindings: mustNotHaveFindings.map(item => ({
        code: item.code,
        codesWithDetails: includeChildCodesNotHave ? item.codesWithDetails : [item.codesWithDetails.find(code => code.code === item.code[0].code)],
        display: item.display,
        count: includeChildCodesNotHave ? item.count : 1
      }))
    };

    try {
      const response = await fetch('/api/cohort/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cohortDefinition)
      });

      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();
      console.log(data);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  return (
    <div style={{ margin: '20px', maxWidth: '600px' }}>
      <h1>Cohort Builder</h1>
      <p>Use this form to create a cohort by defining the selection criteria.</p>

      <Form onSubmit={handleSubmit}>
        <Form.Group className="mb-3" controlId="title">
          <Form.Label>Cohort Title (Required) </Form.Label>
          <Form.Control type="text" placeholder="Title" onChange={(e) => setTitle(e.target.value)} />
        </Form.Group>

        <Form.Group className="mb-3" controlId="gender">
          <Form.Label>Gender (Optional — if none selected, all categories will be considered)</Form.Label>
          {genderOptions.map(({ code, label }) => (
            <Form.Check
              key={code}
              type="checkbox"
              label={label}
              checked={selectedGenders.some(item => item.code === code)}
              onChange={() => handleGenderChange(code, label)}
            />
          ))}
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>Minimum Age: {minAge}</Form.Label>
          <Form.Range min={0} max={120} value={minAge} onChange={(e) => setMinAge(Number(e.target.value))} />
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>Maximum Age: {maxAge}</Form.Label>
          <Form.Range min={0} max={120} value={maxAge} onChange={(e) => setMaxAge(Number(e.target.value))} />
        </Form.Group>

        <Form.Group className="mb-3" controlId="ethnicity">
          <Form.Label>Ethnicity (Optional — if none selected, all categories will be considered)</Form.Label>
          {ethnicityOptions.map(({ code, label }) => (
            <Form.Check
              key={code}
              type="checkbox"
              label={label}
              checked={ethnicity.some(item => item.code === code)}
              onChange={() => handleEthnicityChange(code, label)}
            />
          ))}
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>Time Range (Optional) </Form.Label>
          <Form.Control type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          <Form.Control type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} style={{ marginTop: "5px" }} />
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>Must HAVE Finding / Disorder (Optional)</Form.Label>
          <SnomedSearch
            label=""
            target_code="404684003"
            onSelect={(snomedSelection) => {
              const newCode = snomedSelection.code.code || snomedSelection.code[0]?.code;
              setMustHaveFindings((prev) =>
                prev.some(item => (item.code.code || item.code[0]?.code) === newCode)
                  ? prev
                  : [...prev, snomedSelection]
              );
            }}
          />
          <Form.Check
            type="checkbox"
            label="Include child codes (subsumed concepts)"
            checked={includeChildCodesHave}
            onChange={() => setIncludeChildCodesHave(!includeChildCodesHave)}
            style={{ marginTop: "10px" }}
          />

          {mustHaveFindings.length > 0 && (
            <ul style={{ marginTop: "10px", paddingLeft: "20px" }}>
              {mustHaveFindings.map((item, index) => {
                const displayValue = item.code?.[0]?.display;
                const uniqueId = item.code?.[0]?.code;
                const count = includeChildCodesHave ? item.count : 1;

                return (
                  <li key={uniqueId}>
                    <a
                      href={`https://termbrowser.nhs.uk/?perspective=full&conceptId1=${uniqueId}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ textDecoration: "underline", color: "#007bff" }}
                    >
                      {displayValue}
                    </a>{' '}
                    {`(Include ${count} code${count !== 1 ? 's' : ''})`}
                    <Button
                      variant="outline-danger"
                      size="sm"
                      onClick={() => setMustHaveFindings(prev => prev.filter((_, i) => i !== index))}
                      style={{ marginLeft: "10px", padding: "0 6px" }}
                    >
                      ❌
                    </Button>
                  </li>
                );
              })}
            </ul>
          )}
        </Form.Group>

        <Form.Group className="mb-3">
          <Form.Label>Must NOT HAVE Finding / Disorder (Optional)</Form.Label>
          <SnomedSearch
            label=""
            target_code="404684003"
            onSelect={(snomedSelection) => {
              const newCode = snomedSelection.code.code || snomedSelection.code[0]?.code;
              setMustNotHaveFindings((prev) =>
                prev.some(item => (item.code.code || item.code[0]?.code) === newCode)
                  ? prev
                  : [...prev, snomedSelection]
              );
            }}
          />
          <Form.Check
            type="checkbox"
            label="Include child codes (subsumed concepts)"
            checked={includeChildCodesNotHave}
            onChange={() => setIncludeChildCodesNotHave(!includeChildCodesNotHave)}
            style={{ marginTop: "10px" }}
          />

          {mustNotHaveFindings.length > 0 && (
            <ul style={{ marginTop: "10px", paddingLeft: "20px" }}>
              {mustNotHaveFindings.map((item, index) => {
                const displayValue = item.code?.[0]?.display;
                const uniqueId = item.code?.[0]?.code;
                const count = includeChildCodesNotHave ? item.count : 1;

                return (
                  <li key={uniqueId}>
                    <a
                      href={`https://termbrowser.nhs.uk/?perspective=full&conceptId1=${uniqueId}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ textDecoration: "underline", color: "#007bff" }}
                    >
                      {displayValue}
                    </a>{' '}
                    {`(Include ${count} code${count !== 1 ? 's' : ''})`}
                    <Button
                      variant="outline-danger"
                      size="sm"
                      onClick={() => setMustNotHaveFindings(prev => prev.filter((_, i) => i !== index))}
                      style={{ marginLeft: "10px", padding: "0 6px" }}
                    >
                      ❌
                    </Button>
                  </li>
                );
              })}
            </ul>
          )}
        </Form.Group>

        <Button variant="primary" type="submit">Submit</Button>
      </Form>
    </div>
  );
}

export default App;
