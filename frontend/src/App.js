import './App.css';
import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate } from "react-router-dom";
import { Button, Form, Spinner } from "react-bootstrap";
import SnomedSearch from "./components/SnomedSearch";

import { ethnicityOptions, genderOptions, defaultAgeRange } from './config/formOptions';

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  PieChart, Pie, Cell, ResponsiveContainer
} from 'recharts';

// --- Cohort Form Page ---
function CohortForm() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [selectedGenders, setSelectedGenders] = useState([]);
  const [minAge, setMinAge] = useState(defaultAgeRange.min);
  const [maxAge, setMaxAge] = useState(defaultAgeRange.max);
  const [ethnicity, setEthnicity] = useState([]);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [mustHaveFindings, setMustHaveFindings] = useState([]);
  const [mustNotHaveFindings, setMustNotHaveFindings] = useState([]);
  const [includeChildCodesHave, setIncludeChildCodesHave] = useState(false);
  const [includeChildCodesNotHave, setIncludeChildCodesNotHave] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    document.title = "Patient Cohorting Tool";
  }, []);

  const handleEthnicityChange = (code, label) => {
    setEthnicity(prev => {
      const ethnicityItem = { code, display: label };
      return prev.some(item => item.code === code) ? prev.filter(item => item.code !== code) : [...prev, ethnicityItem];
    });
  };

  const handleGenderChange = (code, label) => {
    setSelectedGenders(prev => {
      const genderItem = { code, display: label };
      return prev.some(item => item.code === code) ? prev.filter(item => item.code !== code) : [...prev, genderItem];
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);

    const cohortDefinition = {
      title,
      gender: selectedGenders.length === 0 ? "ALL" : selectedGenders,
      ageRange: { min: minAge, max: maxAge },
      ethnicity: ethnicity.length === 0 ? "ALL" : ethnicity,
      timeRange: {
        ...(startDate && { start: startDate }),
        ...(endDate && { end: endDate }),
      },
      mustHaveFindings,
      mustNotHaveFindings
    };

    try {
      const response = await fetch('/api/cohort/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cohortDefinition)
      });

      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();

      // Save results and cohort title
      sessionStorage.setItem("resultsData", JSON.stringify(data));
      sessionStorage.setItem("cohortTitle", title);
      window.open("/results", "_blank");

    } catch (error) {
      console.error('Error:', error);
      alert("There was an error processing your request.");
    } finally {
      setLoading(false);
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
      
      <h5 style={{ marginTop: '25px' }}>Summary of Selected Criteria</h5>
      <ul>
        <li><strong>Title:</strong> {title || "N/A"}</li>
        <li><strong>Genders:</strong> {selectedGenders.length === 0 ? "All" : selectedGenders.map((item) => item.display).join(", ")}</li>
        <li><strong>Age Range:</strong> {minAge} - {maxAge}</li>
        <li><strong>Ethnicities:</strong> {ethnicity.length === 0 ? "All" : ethnicity.map((item) => item.display).join(", ")}</li>
        <li><strong>Time Range:</strong> {startDate || endDate ? `${startDate || "Any"} to ${endDate || "Any"}` : "Any"}</li>
        <li><strong>Must Have Findings/Disorders:</strong> {mustHaveFindings.length === 0 ? "None" : mustHaveFindings.map((item) => (item.code && item.code[0] ? item.code[0].display : null)).filter(Boolean).join(", ") || "None"}</li>
        <li><strong>Must Not Have Findings/Disorders:</strong> {mustNotHaveFindings.length === 0 ? "None" : mustNotHaveFindings.map((item) => (item.code && item.code[0] ? item.code[0].display : null)).filter(Boolean).join(", ") || "None"}</li>
      </ul>
    </div>
  );
}

// --- Results Page ---
function ResultsPage() {
  const savedResults = sessionStorage.getItem("resultsData");
  const results = savedResults ? JSON.parse(savedResults) : null;

  if (!results) return <p>No results to display.</p>;

  const genderData = results.genderCounts || [];
  const ageData = results.ageGroups || [];
  const ethnicityData = results.ethnicityCounts || [];
  const topDiagnoses = results.topDiagnoses || [];

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#AA336A'];

  return (
    <div style={{ margin: '20px', maxWidth: '900px' }}>
      <h1>Results for Cohort {results.title || "Untitled"}</h1>
    
      {/* Cohort Summary */}
      <div style={{ marginBottom: '20px' }}>
        <h4>Cohort Summary</h4>
        <p style={{ marginTop: '10px' }}>Total Patients: {results.total_patients || 0}</p>
        {!results.total_patients && (
          <p style={{ color: "red", fontStyle: "italic" }}>No results to display</p>
        )}        
      </div>
    
      {/* Only show charts if patients exist */}
      {results.total_patients > 0 && (
        <>
          <p>Unique Diagnoses: {results.uniqueDiagnoses || 0}</p>
          <p>Age Range: {results.minAge || '-'} - {results.maxAge || '-'}</p>
            
          {/* Gender Distribution */}
          <h3>Gender Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={genderData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="gender" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="count" fill="#8884d8" />
            </BarChart>
          </ResponsiveContainer>
    
          {/* Age Distribution */}
          <h3>Age Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={ageData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="range" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="count" fill="#82ca9d" />
            </BarChart>
          </ResponsiveContainer>
    
          {/* Ethnicity Distribution */}
          <h3 style={{ marginBottom: '20px' }}>Ethnicity Distribution</h3>
          <div style={{ display: "flex", justifyContent: "center", marginBottom: "40px" }}>
            <PieChart width={600} height={350}>
              <Pie
                data={ethnicityData}
                dataKey="count"
                nameKey="ethnicity"
                cx="50%"
                cy="55%"
                outerRadius={120}
                fill="#8884d8"
                label
              >
                {ethnicityData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend verticalAlign="bottom" height={36} />
            </PieChart>
          </div>

          {/* Raw JSON (commented out) */}
          {/*
          <section>
            <h3>Raw Data (JSON)</h3>
            <pre>{JSON.stringify(results, null, 2)}</pre>
          </section>
          */}
        </>
      )}
    </div>
  );
}

// --- App with Router ---
function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<CohortForm />} />
        <Route path="/results" element={<ResultsPage />} />
      </Routes>
    </Router>
  );
}

export default App;
