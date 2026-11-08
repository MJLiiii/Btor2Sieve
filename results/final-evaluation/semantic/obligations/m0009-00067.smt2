(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x7065 (and (distinct s_7 (_ bv0 8)) true)))
(not $x7065)))
(check-sat)
