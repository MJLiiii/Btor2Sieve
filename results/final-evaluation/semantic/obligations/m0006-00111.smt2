(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun s_3 () (_ BitVec 4))
(assert
 true)
(assert
 (let (($x2911 (and (distinct s_3 (_ bv0 4)) true)))
(not $x2911)))
(check-sat)
