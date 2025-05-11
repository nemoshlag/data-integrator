import React, { useEffect, useState } from 'react';
import axios from 'axios';

function App() {
  const [patients, setPatients] = useState([]);

  useEffect(() => {
    axios.get("http://localhost:8000/patients")
      .then(res => setPatients(res.data))
      .catch(err => console.error(err));
  }, []);

  return (
    <div style={{ padding: '20px' }}>
      <h1>Patients admitted more than 48h without Lab Tests</h1>
      <table border="1" cellPadding="10">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Admission Time</th>
            <th>Last Lab Test Time</th>
            <th>Discharge Time</th>
          </tr>
        </thead>
        <tbody>
          {patients.map(p => (
            <tr key={p.id}>
              <td>{p.id}</td>
              <td>{p.name}</td>
              <td>{new Date(p.admission_time).toLocaleString()}</td>
              <td>{p.last_test_time ? new Date(p.last_test_time).toLocaleString() : '-'}</td>
              <td>{p.discharge_time ? new Date(p.discharge_time).toLocaleString() : '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default App;
