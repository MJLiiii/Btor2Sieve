(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x5466 (and (distinct i_7 (_ bv1 8)) true)))
(not $x5466)))
(check-sat)
