(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x293 (and (distinct i_7 (_ bv128 8)) true)))
(not $x293)))
(check-sat)
