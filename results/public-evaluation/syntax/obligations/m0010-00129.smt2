(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x505 (bvsle i_7 (_ bv255 8))))
(not $x505)))
(check-sat)
