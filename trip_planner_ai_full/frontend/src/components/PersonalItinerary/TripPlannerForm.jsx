import React, { useState, useEffect } from 'react';
import {
  Container,
  Paper,
  Grid,
  TextField,
  Autocomplete,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Button,
  Typography,
  Box,
  CircularProgress,
  InputAdornment
} from '@mui/material';
import {
  Flight,
  Home,
  Hotel,
  Terrain,
  AttachMoney,
  ErrorOutline
} from '@mui/icons-material';
import axios from 'axios';
import './plan.css';
import { useNavigate } from 'react-router-dom';

export default function TripPlannerForm({ onSubmit }) {
  const [destinations, setDestinations] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [stayType, setStayType] = useState('hotel');
  const [preferences, setPreferences] = useState('');
  const [budget, setBudget] = useState(1000);
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dateError, setDateError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  // Fetch location suggestions
  useEffect(() => {
    let active = true;
    if (inputValue.length < 3) {
      setOptions([]);
      return;
    }
    setLoading(true);
    axios
      .get(`http://localhost:8000/locations`, { params: { query: inputValue } })
      .then(res => {
        if (active) setOptions(res.data.locations || []);
      })
      .catch(() => {
        if (active) setOptions([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [inputValue]);

  // Validate date order
  useEffect(() => {
    if (startDate && endDate) {
      const start = new Date(startDate);
      const end = new Date(endDate);
      setDateError(start > end ? 'Start must be before end' : '');
    } else {
      setDateError('');
    }
  }, [startDate, endDate]);

  const handleSubmit = async () => {
    console.log(destinations, startDate, endDate, stayType, budget, preferences);
    setSubmitting(true);
    const payload = {
        destinations,
        start_date: startDate,
        end_date: endDate,
        budget,
        preferences,
        stay_type: stayType,
        origin: "SFO" // or let the user choose
      };
    console.log(payload);
    try {
      const response = await fetch('http://localhost:8000/plan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      console.log(data);
      navigate('/personal-itinerary/plan', { state: { plan: data } });
    } catch (error) {
      setSubmitting(false);
      console.error('Error:', error);
      setSubmitting(false);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page-container">
        <Container maxWidth="sm" sx={{ mt: 8, mb: 8 }}>
            <Typography variant="h5" sx={{ mb: 3, fontWeight: 600, color: '#4c1d95' }}>
            Plan Your Trip
            </Typography>
        <Paper elevation={6} sx={{ p: 4, backgroundColor: 'white', borderRadius: 2 }}>

            <Grid container spacing={3}>
            {/* Destination */}
            <Grid item xs={12}>
                <Autocomplete
                    multiple
                    freeSolo
                    options={options}
                    value={destinations}
                    onChange={(e, val) => setDestinations(val)}
                    onInputChange={(e, val) => setInputValue(val)}
                    loading={loading}
                    renderInput={params => (
                        <TextField
                            {...params}
                            label="Destination(s)"
                            placeholder="Search city or country"
                            fullWidth
                        />
                    )}
                />
            </Grid>

            {/* Dates */}
            <Grid item xs={6}>
                <TextField
                label="Start Date"
                type="date"
                fullWidth
                InputLabelProps={{ shrink: true }}
                value={startDate}
                onChange={e => setStartDate(e.target.value)}
                error={!!dateError}
                InputProps={{
                    startAdornment: (
                    <InputAdornment position="start">
                        <Home color="action" />
                    </InputAdornment>
                    )
                }}
                />
            </Grid>
            <Grid item xs={6}>
                <TextField
                label="End Date"
                type="date"
                fullWidth
                InputLabelProps={{ shrink: true }}
                value={endDate}
                onChange={e => setEndDate(e.target.value)}
                error={!!dateError}
                helperText={
                    dateError && (
                    <Box sx={{ display: 'flex', alignItems: 'center', color: 'error.main' }}>
                        <ErrorOutline fontSize="small" sx={{ mr: 0.5 }} />
                        {dateError}
                    </Box>
                    )
                }
                InputProps={{
                    startAdornment: (
                    <InputAdornment position="start">
                        <Hotel color="action" />
                    </InputAdornment>
                    )
                }}
                />
            </Grid>

            {/* Stay Type & Budget */}
            <Grid item xs={6}>
                <FormControl fullWidth>
                <InputLabel>Stay Type</InputLabel>
                <Select
                    value={stayType}
                    label="Stay Type"
                    onChange={e => setStayType(e.target.value)}
                    startAdornment={<Terrain color="action" sx={{ mr: 1 }} />}
                >
                    <MenuItem value="hotel">Hotel</MenuItem>
                    <MenuItem value="camping">Camping</MenuItem>
                    <MenuItem value="glamping">Glamping</MenuItem>
                    <MenuItem value="airbnb">Airbnb</MenuItem>
                </Select>
                </FormControl>
            </Grid>
            <Grid item xs={6}>
                <Typography gutterBottom sx={{ fontWeight: 600 }}>
                Budget: ${budget}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <AttachMoney sx={{ mr: 1 }} />
                <Slider
                    value={budget}
                    min={100}
                    max={5000}
                    step={50}
                    onChange={(e, val) => setBudget(val)}
                    valueLabelDisplay="auto"
                    sx={{ flexGrow: 1 }}
                />
                </Box>
            </Grid>

            {/* Preferences */}
            <Grid item xs={12}>
                <TextField
                label="Preferences"
                multiline
                rows={3}
                fullWidth
                placeholder="e.g. beach, culture, adventure..."
                value={preferences}
                onChange={e => setPreferences(e.target.value)}
                />
            </Grid>

            {/* Submit */}
            <Grid item xs={12}>
                <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                <Button
                    variant="contained"
                    size="large"
                    disabled={!destinations.length || !startDate || !endDate || !!dateError || submitting}
                    onClick={handleSubmit}
                    sx={{
                    backgroundColor: '#4c1d95',
                    textTransform: 'none',
                    px: 4,
                    py: 1.5
                    }}
                >
                    {submitting ? <CircularProgress size={24} sx={{ color: 'white' }} /> : 'Generate Plan'}
                </Button>
                </Box>
            </Grid>
            </Grid>
        </Paper>
        </Container>
    </div>
  );
}
