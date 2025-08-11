// components/PersonalItinerary/PersonalItinerary.jsx
import React, { useMemo, useState } from 'react';
import { useLocation, Navigate } from 'react-router-dom';
import {
  Box, Grid, Paper, Typography, Tabs, Tab, IconButton, Button,
  List, ListItem, ListItemText
} from '@mui/material';
import { ArrowBack, Save, PictureAsPdf } from '@mui/icons-material';
import './plan.css';

export default function PersonalItinerary() {
  const { state } = useLocation() || {};
  const plan = state?.plan;
  console.log(plan, "plan")

  // If user hit the URL directly without state, send them back to the form
  if (!plan) return <Navigate to="/personal-itinerary" replace />;

  const [currentTab, setCurrentTab] = useState(0);
  const tabLabels = ['Summary', 'Flights', 'Hotels', 'Shopping'];

  // Map backend -> UI props and renumber days 1..n
  const { title, days, flights, hotels, shopping } = useMemo(() => {
    const titleStr = `${(plan.destination || []).join(', ')} • ${plan.start_date} → ${plan.end_date}`;

    const daysArr = (plan.day_plans || []).map((d, i) => ({
      label: `D${i + 1}`,
      title: d.title,
      date: d.date,
      items: d.activities || [],
      summary: d.summary || ''
    }));

    const flightsArr = (plan.flights || []).map(f => ({
      airline: f.airline,
      price: f.price,
      departure: f.depart || f.departure,
      arrival: f.arrive || f.arrival,
      link: f.link || null
    }));

    const hotelsArr = (plan.stays || []).map(s => ({
      name: s.name,
      type: s.type,
      price: s.price_per_night,
      nights: s.nights,
      link: s.link || null
    }));

    const shoppingArr = (plan.shopping || []).map(s => ({
      item: s.item,
      reason: s.reason,
      vendor: s.vendor,
      price: s.est_price_usd,
      link: s.link || null
    }));

    return { title: titleStr, days: daysArr, flights: flightsArr, hotels: hotelsArr, shopping: shoppingArr };
  }, [plan]);

  return (
    <Box
      sx={{
        minHeight: '100vh',
        background: 'linear-gradient(to bottom, #fff0f5, #fdf6fa)',
        p: 4,
        fontFamily: 'Inter, sans-serif'
      }}
    >
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, justifyContent: 'space-between' }}>
        <IconButton onClick={() => window.history.back()}>
          <ArrowBack />
        </IconButton>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 700, color: '#6b21a8' }}>
          {title}
        </Typography>
        <Box>
          <Button
            variant="contained"
            startIcon={<Save />}
            sx={{ mr: 1, bgcolor: '#6b21a8', '&:hover': { bgcolor: '#5a1a86' } }}
            onClick={() => console.log('TODO: save plan', plan)}
          >
            Save
          </Button>
          <Button
            variant="outlined"
            startIcon={<PictureAsPdf />}
            sx={{ borderColor: '#6b21a8', color: '#6b21a8' }}
            onClick={() => console.log('TODO: export PDF')}
          >
            Export PDF
          </Button>
        </Box>
      </Box>

      {/* Tabs */}
      <Tabs
        value={currentTab}
        onChange={(e, v) => setCurrentTab(v)}
        indicatorColor="primary"
        textColor="primary"
        sx={{ mb: 4 }}
      >
        {tabLabels.map((label, idx) => (
          <Tab key={idx} label={label} />
        ))}
      </Tabs>

      {/* Summary */}
      {currentTab === 0 && (
        <Grid container spacing={3}>
          {days.map((day, idx) => (
            <Grid item xs={12} sm={6} md={4} key={idx}>
              <Paper sx={{ p: 2, boxShadow: 3, borderRadius: 2 }}>
                <Box display="flex" alignItems="center" mb={1}>
                  <Paper
                    sx={{
                      width: 32,
                      height: 32,
                      borderRadius: '50%',
                      bgcolor: '#fde047',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      mr: 1
                    }}
                  >
                    <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                      {day.label}
                    </Typography>
                  </Paper>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                    {day.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ ml: 'auto' }}>
                    {day.date}
                  </Typography>
                </Box>

                {day.summary && (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {day.summary}
                  </Typography>
                )}

                <List dense>
                  {day.items.map((item, i2) => (
                    <ListItem key={i2} sx={{ pl: 0 }}>
                      <ListItemText primary={`${i2 + 1}. ${item}`} />
                    </ListItem>
                  ))}
                </List>
              </Paper>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Flights */}
      {currentTab === 1 && (
        <Paper sx={{ p: 3, boxShadow: 3 }}>
          <Typography variant="h6" gutterBottom>
            Flight Options
          </Typography>
          <List>
            {flights.map((f, i) => (
              <ListItem
                key={i}
                divider
                secondaryAction={
                  f.link ? (
                    <Button href={f.link} target="_blank" rel="noreferrer">
                      Book
                    </Button>
                  ) : null
                }
              >
                <ListItemText
                  primary={`${f.airline ?? '—'} — ${typeof f.price === 'number' ? `$${f.price}` : '—'}`}
                  secondary={`${f.departure ?? '?'} → ${f.arrival ?? '?'}`}
                />
              </ListItem>
            ))}
            {!flights.length && <Typography>No flight data available.</Typography>}
          </List>
        </Paper>
      )}

      {/* Hotels */}
      {currentTab === 2 && (
        <Paper sx={{ p: 3, boxShadow: 3 }}>
          <Typography variant="h6" gutterBottom>
            Hotel & Stay Options
          </Typography>
          <List>
            {hotels.map((h, i) => (
              <ListItem
                key={i}
                divider
                secondaryAction={
                  h.link ? (
                    <Button href={h.link} target="_blank" rel="noreferrer">
                      Open
                    </Button>
                  ) : null
                }
              >
                <ListItemText
                  primary={`${h.name} — ${typeof h.price === 'number' ? `$${h.price}` : '—'}/night (${h.nights} night${h.nights === 1 ? '' : 's'})`}
                  secondary={h.type}
                />
              </ListItem>
            ))}
            {!hotels.length && <Typography>No accommodations available.</Typography>}
          </List>
        </Paper>
      )}

      {/* Shopping */}
      {currentTab === 3 && (
        <Paper sx={{ p: 3, boxShadow: 3 }}>
          <Typography variant="h6" gutterBottom>
            Shopping Suggestions
          </Typography>
          <List>
            {shopping.map((s, i) => (
              <ListItem
                key={i}
                divider
                secondaryAction={
                  s.link ? (
                    <Button href={s.link} target="_blank" rel="noreferrer">
                      Buy
                    </Button>
                  ) : null
                }
              >
                <ListItemText
                  primary={s.item}
                  secondary={[
                    s.reason,
                    s.vendor ? `Vendor: ${s.vendor}` : null,
                    typeof s.price === 'number' ? `~$${s.price}` : null
                  ]
                    .filter(Boolean)
                    .join(' • ')}
                />
              </ListItem>
            ))}
            {!shopping.length && <Typography>No shopping suggestions.</Typography>}
          </List>
        </Paper>
      )}
    </Box>
  );
}
