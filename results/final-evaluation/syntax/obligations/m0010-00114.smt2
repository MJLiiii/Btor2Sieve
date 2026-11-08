(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x6953 (and (distinct i_7 (_ bv0 8)) true)))
(not $x6953)))
(check-sat)
