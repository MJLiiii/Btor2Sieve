(set-logic ALL)
; benchmark generated from python API
(set-info :status unknown)
(declare-fun i_7 () (_ BitVec 8))
(declare-fun i_6 () (_ BitVec 8))
(assert
 true)
(assert
 (let (($x541 (= i_6 i_7)))
(not $x541)))
(check-sat)
